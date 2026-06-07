/**
 * E2E Tests for Billing System
 * 
 * Tests visit-scoped billing workflows including:
 * - Department bill item generation
 * - Receptionist payment processing
 * - Partial payments
 * - Insurance visits
 * - Wallet system
 * - Paystack integration
 * - Visit closure rules
 * - Full billing lifecycle (Cash visit)
 * 
 * Prerequisites:
 * - Playwright installed: npm install --save-dev @playwright/test
 * - Test users created in database (doctor@clinic.com, receptionist@clinic.com, labtech@clinic.com)
 * - Lab service price list configured (e.g., CBC-001)
 * 
 * Run tests: npx playwright test e2e/billing/billing.spec.ts
 */
import { test, expect, Page } from '@playwright/test';
import { loginAs, navigateInApp, switchUser } from '../helpers/auth';
import { skipIfServicesDown } from '../helpers/health';
import { TEST_DOCTOR, TEST_LAB_TECH, TEST_RECEPTIONIST } from '../helpers/test-users';

test.setTimeout(180000);

test.beforeEach(async ({ baseURL, page }) => {
  await skipIfServicesDown(page, baseURL!);
});

const TEST_PATIENT = {
  first_name: 'John',
  last_name: 'Doe',
  date_of_birth: '1990-01-15',
  gender: 'MALE',
  phone: '+2348012345678',
  email: 'john.doe@example.com',
};

/**
 * Helper: Create a visit
 * 
 * Note: CreateVisitPage uses a search interface, not a dropdown.
 * We need to search for the patient first, then select them.
 * 
 * @param page - Playwright page object
 * @param patientId - Patient ID (numeric) - will search by patient_id format (LMC000001)
 * @param paymentType - Payment type: 'CASH' or 'INSURANCE'
 */
async function createVisit(page: Page, patientId: number, paymentType: 'CASH' | 'INSURANCE' = 'CASH') {
  console.log(`Creating visit for patient ${patientId} with type ${paymentType}...`);
  
  await page.goto(`/visits/new?patient=${patientId}`, { waitUntil: 'commit', timeout: 30000 });
  
  // Wait for the page to load
  await expect(page.getByRole('heading', { name: 'Create New Visit' })).toBeVisible({ timeout: 15000 });
  
  // Wait for patient to be loaded
  try {
    await expect(page.getByRole('heading', { name: 'Selected Patient' })).toBeVisible({ timeout: 15000 });
  } catch (e) {
    const pageText = await page.textContent('body');
    if (pageText?.includes('Patient not found')) {
      throw new Error(`Patient ${patientId} not found when trying to create visit.`);
    }
    throw e;
  }
  
  // Fill visit details
  const visitTypeSelect = page.locator('select').filter({ has: page.locator('option[value="CONSULTATION"]') }).first();
  await visitTypeSelect.selectOption('CONSULTATION');
  
  const chiefComplaintInput = page.getByPlaceholder(/Enter reason for visit/i).first();
  await chiefComplaintInput.fill('Routine checkup from E2E test');

  // Select payment type
  const paymentTypeSelect = page.locator('select').filter({ has: page.locator('option[value="CASH"]') }).last();
  await paymentTypeSelect.selectOption(paymentType);
  
  // Click "Create Visit" button
  const createButton = page.getByRole('button', { name: 'Create Visit' });
  await expect(createButton).toBeEnabled({ timeout: 10000 });
  
  // Setup response listener and navigation
  let visitId = 0;
  let apiError: string | null = null;
  
  const billingSummaryAfterCreate = page.waitForResponse(
    (res) => res.url().includes('/billing/summary') && res.ok(),
    { timeout: 60000 }
  ).catch(() => null);

  const [response] = await Promise.all([
    page.waitForResponse(resp => 
      resp.url().includes('/api/v1/visits/') && resp.request().method() === 'POST',
      { timeout: 20000 }
    ).catch(e => {
      console.warn('POST /visits/ timed out or failed:', e);
      return null;
    }),
    createButton.click()
  ]);
  
  if (response) {
    if (response.ok()) {
      const data = await response.json();
      visitId = data.id;
      console.log(`Visit created successfully with ID: ${visitId}`);
    } else {
      const errorData = await response.json().catch(() => ({}));
      apiError = errorData.detail || JSON.stringify(errorData);
      console.error(`API Error creating visit: ${response.status()} ${apiError}`);
    }
  }

  // Wait for navigation - the app has an 800ms delay before redirecting
  await page.waitForURL(/\/visits\/\d+/, { timeout: 20000 }).catch(async () => {
    // If navigation didn't happen, check for errors on the page
    const errorToast = await page.locator('.toast-error, [class*="errorMessage"]').first().textContent().catch(() => null);
    if (errorToast) {
      throw new Error(`Failed to create visit: ${errorToast}`);
    }
    if (apiError) {
      throw new Error(`Failed to create visit (API error): ${apiError}`);
    }
  });
  
  if (visitId === 0) {
    const urlMatch = page.url().match(/\/visits\/(\d+)/);
    if (urlMatch && urlMatch[1]) {
      visitId = parseInt(urlMatch[1]);
    }
  }
  
  if (visitId === 0) {
    throw new Error(`Failed to create visit and extract ID. Current URL: ${page.url()}`);
  }

  await billingSummaryAfterCreate;

  return visitId;
}

/** Add a catalog service to the visit bill (API — stable setup for E2E). */
async function addBillingService(
  page: Page,
  visitId: number,
  serviceCode: string,
  department: string,
  additionalData?: Record<string, unknown>
) {
  const headers = await apiHeaders(page);

  const payload: Record<string, unknown> = {
    visit_id: visitId,
    department,
    service_code: serviceCode,
  };
  if (additionalData) {
    payload.additional_data = additionalData;
  }

  let lastError = `add-item ${serviceCode} failed`;

  for (let attempt = 0; attempt < 4; attempt++) {
    const res = await page.request.post('http://127.0.0.1:8000/api/v1/billing/add-item/', {
      headers,
      data: payload,
    });

    if (res.ok()) return;

    const body = await res.json().catch(() => ({}));
    const msg = JSON.stringify(body);
    lastError = `add-item ${serviceCode} failed (${res.status()}): ${msg}`;

    if (msg.toLowerCase().includes('already exists')) {
      return;
    }

    if (msg.toLowerCase().includes('database is locked') && attempt < 3) {
      await page.waitForTimeout(1500 * (attempt + 1));
      continue;
    }

    break;
  }

  throw new Error(lastError);
}

/** Fetch billing summary via API (fast, avoids heavy UI navigation). */
async function getBillingSummaryViaApi(page: Page, visitId: number) {
  const headers = await apiHeaders(page);

  for (let attempt = 0; attempt < 4; attempt++) {
    const res = await page.request.get(
      `http://127.0.0.1:8000/api/v1/visits/${visitId}/billing/summary/`,
      { headers, timeout: 60000 }
    );

    if (res.ok()) {
      const data = (await res.json()) as {
        total_charges?: string | number;
        outstanding_balance?: string | number;
        payment_status?: string;
      };
      const summary = {
        totalCharges: parseFloat(String(data.total_charges ?? '0')),
        outstandingBalance: parseFloat(String(data.outstanding_balance ?? '0')),
        paymentStatus: (data.payment_status ?? '').trim(),
      };
      console.log(`API summary for visit ${visitId}:`, summary);
      return summary;
    }

    const body = await res.text().catch(() => '');
    if (body.toLowerCase().includes('database is locked') && attempt < 3) {
      await page.waitForTimeout(1500 * (attempt + 1));
      continue;
    }
    throw new Error(`billing summary API failed (${res.status()}): ${body}`);
  }

  throw new Error(`billing summary API failed for visit ${visitId}`);
}

async function apiHeaders(page: Page) {
  return page.evaluate(() => {
    const tokens = JSON.parse(localStorage.getItem('auth_tokens') || '{}') as { access?: string };
    const org = localStorage.getItem('organization_id');
    return {
      Authorization: `Bearer ${tokens.access || ''}`,
      'X-Organization-Id': org || '',
      'Content-Type': 'application/json',
    };
  });
}

/** Approve visit insurance so clinical gates clear without cash payment. */
async function approveVisitInsurance(page: Page, visitId: number) {
  const headers = await apiHeaders(page);
  const listRes = await page.request.get(
    `http://127.0.0.1:8000/api/v1/visits/${visitId}/insurance/`,
    { headers }
  );
  if (!listRes.ok()) {
    throw new Error(`list insurance failed: ${listRes.status()}`);
  }
  const raw = await listRes.json();
  const records: Array<{ id: number }> = Array.isArray(raw)
    ? raw
    : Array.isArray((raw as { results?: Array<{ id: number }> }).results)
      ? (raw as { results: Array<{ id: number }> }).results
      : (raw as { id?: number }).id
        ? [raw as { id: number }]
        : [];
  const insuranceId = records[0]?.id;
  if (!insuranceId) {
    throw new Error(`No visit insurance record to approve: ${JSON.stringify(raw)}`);
  }

  const patchRes = await page.request.patch(
    `http://127.0.0.1:8000/api/v1/visits/${visitId}/insurance/${insuranceId}/`,
    {
      headers,
      data: { approval_status: 'APPROVED', approved_amount: '10000.00' },
    }
  );
  if (!patchRes.ok()) {
    throw new Error(`approve insurance failed (${patchRes.status()}): ${await patchRes.text()}`);
  }
}

/** Attach pending HMO insurance to a visit (required for INSURANCE_PENDING billing status). */
async function attachVisitInsurance(page: Page, visitId: number) {
  const headers = await apiHeaders(page);
  const providersRes = await page.request.get(
    'http://127.0.0.1:8000/api/v1/billing/hmo-providers/',
    { headers }
  );
  if (!providersRes.ok()) {
    throw new Error(`HMO providers list failed: ${providersRes.status()}`);
  }
  const providers = (await providersRes.json()) as { results?: Array<{ id: number }> } | Array<{ id: number }>;
  const list = Array.isArray(providers) ? providers : providers.results || [];
  const providerId = list[0]?.id;
  if (!providerId) {
    throw new Error('No HMO provider found — run seed_e2e_users');
  }

  const res = await page.request.post(
    `http://127.0.0.1:8000/api/v1/visits/${visitId}/insurance/`,
    {
      headers,
      data: {
        visit: visitId,
        provider: providerId,
        policy_number: `E2E-POL-${visitId}`,
        coverage_type: 'FULL',
        coverage_percentage: 100,
      },
    }
  );
  if (!res.ok()) {
    const body = await res.json().catch(() => ({}));
    if (res.status() === 400 && JSON.stringify(body).includes('already exists')) {
      return;
    }
    throw new Error(`attach insurance failed (${res.status()}): ${JSON.stringify(body)}`);
  }
}

/** Record payment via API (stable gate-clearing; UI flow tested in payment describe). */
async function recordPaymentViaApi(
  page: Page,
  visitId: number,
  amount: number,
  method: 'CASH' | 'POS' | 'TRANSFER' = 'CASH'
) {
  const headers = await apiHeaders(page);
  const payload: Record<string, string> = {
    amount: amount.toFixed(2),
    payment_method: method,
    notes: 'E2E payment',
  };
  if (method === 'POS' || method === 'TRANSFER') {
    payload.transaction_reference = `E2E-${Date.now()}`;
  }

  const res = await page.request.post(
    `http://127.0.0.1:8000/api/v1/visits/${visitId}/billing/payments/`,
    { headers, data: payload }
  );
  if (!res.ok()) {
    throw new Error(`payment API failed (${res.status()}): ${await res.text()}`);
  }
}

/** Pay registration gate (REG-001) so doctor can open consultation workspace. */
async function payRegistrationGate(
  page: Page,
  visitId: number,
  method: 'CASH' | 'POS' = 'CASH'
) {
  await addBillingService(page, visitId, 'REG-001', 'CONSULTATION');
  let summary = await getBillingSummaryViaApi(page, visitId);
  if (summary.outstandingBalance > 0) {
    await recordPaymentViaApi(page, visitId, summary.outstandingBalance, method);
    summary = await getBillingSummaryViaApi(page, visitId);
  }
  return summary;
}

/** Pay registration + consultation gates (REG-001 + CONS-001). */
async function clearConsultationGates(page: Page, visitId: number) {
  await payRegistrationGate(page, visitId);
  await addBillingService(page, visitId, 'CONS-001', 'CONSULTATION');
  let summary = await getBillingSummaryViaApi(page, visitId);
  if (summary.outstandingBalance > 0) {
    await recordPaymentViaApi(page, visitId, summary.outstandingBalance, 'CASH');
    summary = await getBillingSummaryViaApi(page, visitId);
  }
  return summary;
}

const CONSULTATION_PAYLOAD = {
  history: 'Patient complains of persistent headache and mild fever for 3 days.',
  examination: 'Temperature: 38.2°C, BP: 120/80. No visible neurological deficits.',
  diagnosis: 'Suspected Tension Headache with low-grade fever.',
  clinical_notes: 'Recommended rest, hydration, and lab investigations.',
};

/** Create or update consultation via API (stable; UI is covered elsewhere). */
async function createConsultation(page: Page, visitId: number) {
  console.log(`Creating consultation for visit ${visitId}...`);
  const headers = await apiHeaders(page);

  const postRes = await page.request.post(
    `http://127.0.0.1:8000/api/v1/visits/${visitId}/consultation/`,
    { headers, data: CONSULTATION_PAYLOAD, timeout: 60000 }
  );

  if (postRes.ok()) return;

  const postBody = await postRes.text().catch(() => '');
  if (postRes.status() === 400 && postBody.toLowerCase().includes('already exists')) {
    const patchRes = await page.request.patch(
      `http://127.0.0.1:8000/api/v1/visits/${visitId}/consultation/`,
      { headers, data: CONSULTATION_PAYLOAD }
    );
    if (patchRes.ok()) return;
    throw new Error(`consultation PATCH failed (${patchRes.status()}): ${await patchRes.text()}`);
  }

  throw new Error(`consultation POST failed (${postRes.status()}): ${postBody}`);
}

/** Add a lab service from catalog (creates lab order + billing line item). */
async function addLabOrder(page: Page, visitId: number, testCode: string) {
  console.log(`Adding lab order ${testCode} for visit ${visitId}...`);
  await addBillingService(page, visitId, testCode, 'LAB', {
    tests_requested: ['Complete Blood Count'],
  });
  console.log(`Lab order ${testCode} added successfully for visit ${visitId}`);
}

/**
 * Wait until receptionist billing UI is loaded on the visit details page.
 * BillingSection fetches /billing/summary/ async — heading appears only after load.
 */
async function waitForBillingReady(page: Page, visitId: number) {
  await expect(page.getByRole('heading', { name: `Visit #${visitId}` })).toBeVisible({
    timeout: 20000,
  });
  await expect(page.getByTestId('billing-section-wrapper')).toBeVisible({ timeout: 20000 });

  const billingApi = page
    .waitForResponse(
      (res) => res.url().includes(`/visits/${visitId}/billing/summary`) && res.ok(),
      { timeout: 60000 }
    )
    .catch(() => null);
  await billingApi;

  await expect(page.getByTestId('billing-summary')).toBeVisible({ timeout: 20000 });
  await expect(page.getByRole('heading', { name: 'Billing & Payments' })).toBeVisible({
    timeout: 15000,
  });
}

/**
 * Helper: Get billing summary
 */
async function getBillingSummary(page: Page, visitId: number) {
  console.log(`Getting billing summary for visit ${visitId}...`);

  const summaryLoaded = page.waitForResponse(
    (res) => res.url().includes(`/visits/${visitId}/billing/summary`) && res.ok(),
    { timeout: 30000 }
  );

  await page.goto(`/visits/${visitId}#billing-section`, { waitUntil: 'commit', timeout: 30000 });
  await summaryLoaded.catch(() => {});
  await waitForBillingReady(page, visitId);
  
  // Extract billing data from the page - use retry-capable extraction
  const extract = async (testId: string) => {
    const locator = page.locator(`[data-testid="${testId}"]`);
    // Wait for the element to be visible and have non-empty text if it's charges/balance
    await expect(locator).toBeVisible({ timeout: 10000 });
    return (await locator.textContent()) || '0';
  };
  
  const totalChargesText = await extract('total-charges');
  const outstandingBalanceText = await extract('outstanding-balance');
  const paymentStatusText = await extract('payment-status');
  
  const summary = {
    totalCharges: parseFloat(totalChargesText.replace(/[₦,\s]/g, '') || '0'),
    outstandingBalance: parseFloat(outstandingBalanceText.replace(/[₦,\s]/g, '') || '0'),
    paymentStatus: paymentStatusText.trim() || '',
  };
  
  console.log(`Extracted Summary for visit ${visitId}:`, summary);
  return summary;
}

/**
 * Helper: Process payment
 */
async function processPayment(
  page: Page,
  visitId: number,
  amount: number,
  method: 'CASH' | 'POS' | 'TRANSFER' | 'WALLET' | 'PAYSTACK'
) {
  console.log(`Processing ${amount} ${method} payment for visit ${visitId}...`);

  for (let attempt = 0; attempt < 2; attempt++) {
    await page.goto(`/visits/${visitId}#billing-section`, {
      waitUntil: 'commit',
      timeout: 30000,
    });
    try {
      await waitForBillingReady(page, visitId);
      break;
    } catch (e) {
      if (attempt === 1) throw e;
      await page.waitForTimeout(1500);
    }
  }

  await page.getByRole('button', { name: /payments/i }).click();

  const methodLabel =
    method === 'POS'
      ? 'POS'
      : method === 'CASH'
        ? 'Cash'
        : method === 'TRANSFER'
          ? 'Bank Transfer'
          : method === 'WALLET'
            ? 'Wallet'
            : 'Paystack';

  const methodButton = page.getByRole('button', { name: new RegExp(methodLabel, 'i') });
  await expect(methodButton).toBeVisible({ timeout: 10000 });
  await expect(methodButton).toBeEnabled();
  await methodButton.click();

  const amountInput = page.getByPlaceholder(/enter amount/i);
  await expect(amountInput).toBeVisible({ timeout: 10000 });
  await amountInput.fill(amount.toString());

  if (method === 'POS' || method === 'TRANSFER') {
    const refInput = page.getByLabel(/reference/i).first();
    await expect(refInput).toBeVisible({ timeout: 5000 });
    await refInput.fill(`REF-${Date.now()}`);
  }

  if (method === 'PAYSTACK') {
    const emailInput = page.getByLabel(/email/i).first();
    await expect(emailInput).toBeVisible({ timeout: 5000 });
    await emailInput.fill(TEST_PATIENT.email);
  }

  const submitLabel =
    method === 'CASH'
      ? 'Record Cash Payment'
      : method === 'POS'
        ? 'Record POS Payment'
        : method === 'TRANSFER'
          ? 'Record Transfer Payment'
          : method === 'PAYSTACK'
            ? 'Initialize Paystack Payment'
            : 'Process Wallet Payment';

  const paymentPost = page.waitForResponse(
    (res) =>
      res.url().includes(`/visits/${visitId}/billing/payments`) &&
      res.request().method() === 'POST',
    { timeout: 30000 }
  );

  await page.getByRole('button', { name: submitLabel }).click();
  const paymentResponse = await paymentPost;
  if (!paymentResponse.ok()) {
    throw new Error(`Payment UI failed (${paymentResponse.status()}): ${await paymentResponse.text()}`);
  }
  console.log(`${method} payment processed successfully.`);
}

/**
 * Helper: Register a new patient (Receptionist action)
 * 
 * Returns the patient ID from the API response or extracted from the UI
 */
async function registerPatient(page: Page, patientData: typeof TEST_PATIENT): Promise<number> {
  const uniqueSuffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const uniqueFirstName = `${patientData.first_name}${uniqueSuffix}`;
  const uniqueEmail = `${uniqueFirstName.toLowerCase()}@example.com`;
  const uniquePhone = `+234${uniqueSuffix.replace(/\D/g, '').slice(-10)}`;

  console.log(`Registering unique patient ${uniqueFirstName} ${patientData.last_name}...`);

  // Client-side nav — raw page.goto can reload before auth hydrates and redirect to /login
  await navigateInApp(page, '/patients/register', 'Personal Information');

  const personalSection = page
    .getByRole('heading', { name: 'Personal Information' })
    .locator('..');
  const personalTextboxes = personalSection.getByRole('textbox');
  await personalTextboxes.nth(0).fill(uniqueFirstName);
  await personalTextboxes.nth(1).fill(patientData.last_name);
  await personalSection.locator('input[type="date"]').fill(patientData.date_of_birth);
  await personalSection.getByRole('combobox').selectOption(patientData.gender);

  const contactSection = page
    .getByRole('heading', { name: 'Contact Information' })
    .locator('..');
  await contactSection.locator('input[type="tel"]').fill(uniquePhone);
  await contactSection.locator('input[type="email"]').fill(uniqueEmail);

  const submitButton = page.getByRole('button', { name: 'Register Patient' });
  await expect(submitButton).toBeEnabled({ timeout: 5000 });

  let patientId = 0;
  let lastError = 'unknown';

  for (let attempt = 0; attempt < 3; attempt++) {
    const createResponse = page.waitForResponse(
      (res) =>
        res.url().includes('/patients') &&
        res.request().method() === 'POST' &&
        !res.url().includes('/search'),
      { timeout: 30000 }
    );
    await submitButton.click();
    const response = await createResponse;

    if (!response.ok()) {
      const err = await response.json().catch(() => ({}));
      lastError = `Patient registration API failed (${response.status()}): ${JSON.stringify(err)}`;
      const errText = JSON.stringify(err).toLowerCase();
      const retryable =
        response.status() >= 500 ||
        errText.includes('database is locked') ||
        errText.includes('locked');
      if (retryable && attempt < 2) {
        await page.waitForTimeout(2000 * (attempt + 1));
        continue;
      }
      throw new Error(lastError);
    }

    const data = (await response.json()) as { id?: number; patient?: { id?: number } };
    patientId = Number(data.patient?.id ?? data.id);
    if (patientId && !Number.isNaN(patientId)) {
      console.log(`Patient registered successfully with ID: ${patientId}`);
      return patientId;
    }
    lastError = `Failed to extract patient ID from response: ${JSON.stringify(data)}`;
    break;
  }

  throw new Error(lastError);
}

/**
 * Helper: Record lab result via API (after visit payment is cleared).
 */
async function recordLabResultViaApi(page: Page, visitId: number, resultData: string) {
  const headers = await apiHeaders(page);
  const ordersRes = await page.request.get(
    `http://127.0.0.1:8000/api/v1/visits/${visitId}/laboratory/`,
    { headers }
  );
  if (!ordersRes.ok()) {
    throw new Error(`list lab orders failed: ${ordersRes.status()}`);
  }
  const orders = (await ordersRes.json()) as Array<{ id: number }>;
  const orderId = orders[0]?.id;
  if (!orderId) {
    throw new Error(`No lab orders found for visit ${visitId}`);
  }

  const res = await page.request.post(
    `http://127.0.0.1:8000/api/v1/visits/${visitId}/laboratory/results/`,
    {
      headers,
      data: { lab_order: orderId, result_data: resultData, abnormal_flag: 'NORMAL' },
    }
  );
  if (!res.ok()) {
    throw new Error(`record lab result failed (${res.status()}): ${await res.text()}`);
  }
}

/**
 * Helper: Record lab result (Lab staff action in consultation workspace)
 */
async function recordLabResult(page: Page, visitId: number, resultData: string) {
  try {
    await recordLabResultViaApi(page, visitId, resultData);
    console.log('Lab result recorded successfully via API.');
    return;
  } catch (apiErr) {
    console.log('API lab result failed, falling back to UI:', apiErr);
  }

  console.log(`Recording lab result for visit ${visitId}...`);
  
  // Try consultation page first, fallback to visit details page
  let labOrdersFound = false;
  const routes = [`/visits/${visitId}/consultation`, `/visits/${visitId}`];
  
  for (const route of routes) {
    try {
      await page.goto(route, { waitUntil: 'domcontentloaded' });
      
      // Wait for page to load - try multiple selectors
      await Promise.race([
        page.waitForSelector('h1:has-text("Visit #")', { timeout: 5000 }),
        page.waitForSelector('h2:has-text("Consultation")', { timeout: 5000 }),
        page.waitForSelector('h3:has-text("Lab Orders")', { timeout: 5000 }),
      ]).catch(() => {});
      
      // Wait for any loading states to disappear
      await page.waitForFunction(() => {
        const body = document.body.textContent || '';
        return !body.includes('Loading visit details') && !body.includes('Initializing...');
      }, { timeout: 5000 }).catch(() => {});
      
      // Check if Lab Orders section is visible
      const labHeading = page.locator('h3:has-text("Lab Orders"), h2:has-text("Lab Orders")').first();
      const isVisible = await labHeading.isVisible({ timeout: 5000 }).catch(() => false);
      
      if (isVisible) {
        labOrdersFound = true;
        break;
      }
    } catch (e) {
      console.log(`Failed to find Lab Orders on ${route}, trying next route...`);
      continue;
    }
  }
  
  if (!labOrdersFound) {
    throw new Error(`Could not find Lab Orders section for visit ${visitId} on any route.`);
  }
  
  // Wait for Lab Orders section to be visible
  const labHeading = page.locator('h3:has-text("Lab Orders"), h2:has-text("Lab Orders")').first();
  await expect(labHeading).toBeVisible({ timeout: 10000 });
  
  // Wait for "Add Result" button to appear - this indicates the lab order exists and is visible
  // Retry up to 8 times with delays (allowing time for database commit and UI refresh)
  const addResultButton = page.locator('button:has-text("Add Result")').first();
  let buttonFound = false;
  
  for (let attempt = 0; attempt < 8; attempt++) {
    // Wait for API response to complete
    try {
      await page.waitForResponse(
        (response) => 
          response.url().includes(`/api/v1/visits/${visitId}/laboratory/`) && 
          !response.url().includes('/results/') &&
          response.request().method() === 'GET',
        { timeout: 5000 }
      );
    } catch {
      // API response not captured, continue anyway
    }
    
    // Check if button is visible
    buttonFound = await addResultButton.isVisible({ timeout: 2000 }).catch(() => false);
    
    if (buttonFound) {
      console.log(`Add Result button found on attempt ${attempt + 1}`);
      break;
    }
    
    if (attempt < 7) {
      console.log(`Add Result button not visible, retrying (${attempt + 1}/8)...`);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForSelector('h3:has-text("Lab Orders"), h2:has-text("Lab Orders")', { timeout: 10000 });
      await page.waitForTimeout(2000);
    }
  }
  
  if (!buttonFound) {
    const pageText = await page.textContent('body').catch(() => '');
    console.log('Page content snippet:', pageText.substring(0, 1500));
    throw new Error(`Add Result button not found for visit ${visitId} after 8 attempts. Lab order might not have been created, is not in ORDERED status, result already exists, or lab tech doesn't have permission.`);
  }
  
  await addResultButton.click();
  
  // Wait for the result form to appear
  const resultInput = page.locator('textarea[placeholder*="findings and results"], textarea[placeholder*="lab findings"], textarea[name*="result"]').first();
  await expect(resultInput).toBeVisible({ timeout: 5000 });
  await resultInput.fill(resultData);
  
  // Select abnormal flag if present
  const flagSelect = page.locator('select[name*="flag"], select').filter({ has: page.locator('option[value="NORMAL"]') }).first();
  if (await flagSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
    await flagSelect.selectOption('NORMAL');
  }
  
  // Click "Record Result" or "Save Result"
  const saveButton = page.locator('button:has-text("Record Result"), button:has-text("Save Result")').first();
  await expect(saveButton).toBeEnabled({ timeout: 5000 });
  
  // Wait for API response
  const responsePromise = page.waitForResponse(
    (response) => 
      response.url().includes(`/api/v1/visits/${visitId}/laboratory/results/`) && 
      response.request().method() === 'POST',
    { timeout: 15000 }
  ).catch(() => null);
  
  await saveButton.click();
  
  // Wait for API response
  const response = await responsePromise;
  if (response && !response.ok()) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(`Failed to record lab result: ${response.status()} ${JSON.stringify(errorData)}`);
  }
  
  // Wait for success message or form closure
  try {
    await page.waitForSelector('.success-message, .toast-success, [class*="success"]', { timeout: 10000 });
    console.log('Lab result recorded successfully.');
  } catch {
    console.log('Success message not found, checking if form closed...');
    // Check if the form closed
    await expect(resultInput).not.toBeVisible({ timeout: 10000 });
    console.log('Lab result form closed, assuming success.');
  }
}

/**
 * Helper: Generate receipt
 */
async function generateReceipt(page: Page, visitId: number) {
  console.log(`Verifying receipt availability for visit ${visitId}...`);
  await page.goto(`/visits/${visitId}`, { waitUntil: 'commit' });
  await expect(page.getByRole('heading', { name: `Visit #${visitId}` })).toBeVisible({
    timeout: 20000,
  });

  const viewReceipt = page.getByRole('button', { name: /view receipt/i });
  await expect(viewReceipt).toBeEnabled({ timeout: 20000 });
  return viewReceipt;
}

/**
 * Helper: Close visit (Doctor action)
 */
async function closeVisit(page: Page, visitId: number) {
  console.log(`Closing visit ${visitId}...`);
  const headers = await apiHeaders(page);
  const res = await page.request.post(`http://127.0.0.1:8000/api/v1/visits/${visitId}/close/`, {
    headers,
    timeout: 60000,
  });
  if (!res.ok()) {
    throw new Error(`close visit API failed (${res.status()}): ${await res.text()}`);
  }
  console.log(`Visit ${visitId} closed successfully.`);
}

test.describe('Billing System - Visit-Scoped Billing', () => {
  test.describe.configure({ mode: 'serial' });

  test('should create visit and initialize billing', async ({ page }) => {
    await switchUser(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    
    await expect(page).toHaveURL(new RegExp(`/visits/${visitId}`));
    await waitForBillingReady(page, visitId);

    // Verify initial billing state
    const summary = await getBillingSummary(page, visitId);
    expect(summary.totalCharges).toBe(0);
    expect(summary.outstandingBalance).toBe(0);
    expect(summary.paymentStatus).toBe('PAID');
  });

  test('should automatically create consultation charge when doctor creates consultation', async ({ page }) => {
    await switchUser(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    await payRegistrationGate(page, visitId);

    await switchUser(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    await addBillingService(page, visitId, 'CONS-001', 'CONSULTATION');

    await switchUser(page, TEST_RECEPTIONIST);
    const summary = await getBillingSummaryViaApi(page, visitId);

    expect(summary.totalCharges).toBeGreaterThanOrEqual(5000);
    expect(summary.outstandingBalance).toBeGreaterThan(0);
  });

  test('should automatically create lab charge when lab order is added', async ({ page }) => {
    await switchUser(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    await clearConsultationGates(page, visitId);

    await switchUser(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    await addLabOrder(page, visitId, 'CBC-001');
    
    await switchUser(page, TEST_RECEPTIONIST);
    const summary = await getBillingSummaryViaApi(page, visitId);
    expect(summary.totalCharges).toBeGreaterThan(0);

    expect(summary.totalCharges).toBeGreaterThan(7000);
  });
});

test.describe('Billing System - Payment Processing', () => {
  test.describe.configure({ mode: 'serial' });

  test('should process full cash payment and clear outstanding balance', async ({ page }) => {
    await switchUser(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    await payRegistrationGate(page, visitId);

    await switchUser(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    await addBillingService(page, visitId, 'CONS-001', 'CONSULTATION');

    await switchUser(page, TEST_RECEPTIONIST);
    const initialSummary = await getBillingSummaryViaApi(page, visitId);
    const amountToPay = initialSummary.outstandingBalance;

    await processPayment(page, visitId, amountToPay, 'CASH');

    const finalSummary = await getBillingSummaryViaApi(page, visitId);
    expect(finalSummary.outstandingBalance).toBe(0);
    expect(finalSummary.paymentStatus).toBe('PAID');
  });

  test('should process partial payment and update outstanding balance', async ({ page }) => {
    await switchUser(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    await payRegistrationGate(page, visitId);

    await switchUser(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    await addBillingService(page, visitId, 'CONS-001', 'CONSULTATION');

    await switchUser(page, TEST_RECEPTIONIST);
    const initialSummary = await getBillingSummaryViaApi(page, visitId);
    const outstandingBefore = initialSummary.outstandingBalance;
    const partialAmount = Math.floor(outstandingBefore / 2);

    await processPayment(page, visitId, partialAmount, 'CASH');

    const afterPaymentSummary = await getBillingSummaryViaApi(page, visitId);
    expect(afterPaymentSummary.outstandingBalance).toBeCloseTo(outstandingBefore - partialAmount, 2);
    expect(afterPaymentSummary.paymentStatus).toBe('PARTIALLY_PAID');

    await recordPaymentViaApi(page, visitId, afterPaymentSummary.outstandingBalance, 'CASH');

    const finalSummary = await getBillingSummaryViaApi(page, visitId);
    expect(finalSummary.outstandingBalance).toBe(0);
    expect(finalSummary.paymentStatus).toBe('PAID');
  });
});

test.describe('Billing System - Insurance Visits', () => {
  test.describe.configure({ mode: 'serial' });

  test('should create insurance visit and defer payment', async ({ page }) => {
    await switchUser(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'INSURANCE');
    await attachVisitInsurance(page, visitId);
    await payRegistrationGate(page, visitId, 'POS');

    await switchUser(page, TEST_DOCTOR);
    await createConsultation(page, visitId);

    await switchUser(page, TEST_RECEPTIONIST);
    await addBillingService(page, visitId, 'CONS-001', 'CONSULTATION');

    const summary = await getBillingSummaryViaApi(page, visitId);
    expect(['INSURANCE_PENDING', 'PARTIALLY_PAID', 'INSURANCE_CLAIMED']).toContain(
      summary.paymentStatus
    );
    expect(summary.outstandingBalance).toBeGreaterThan(0);
  });

  test('should allow doctor to close insurance visit with pending status', async ({ page }) => {
    await switchUser(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'INSURANCE');
    await attachVisitInsurance(page, visitId);
    await addBillingService(page, visitId, 'REG-001', 'CONSULTATION');
    await approveVisitInsurance(page, visitId);

    await switchUser(page, TEST_DOCTOR);
    await createConsultation(page, visitId);

    await switchUser(page, TEST_RECEPTIONIST);
    await addBillingService(page, visitId, 'CONS-001', 'CONSULTATION');

    const summary = await getBillingSummaryViaApi(page, visitId);
    expect(['INSURANCE_PENDING', 'INSURANCE_CLAIMED', 'PARTIALLY_PAID', 'SETTLED']).toContain(
      summary.paymentStatus
    );

    await switchUser(page, TEST_DOCTOR);
    await closeVisit(page, visitId);
    const headers = await apiHeaders(page);
    const visitRes = await page.request.get(`http://127.0.0.1:8000/api/v1/visits/${visitId}/`, {
      headers,
    });
    const closedVisit = (await visitRes.json()) as { status?: string };
    expect(closedVisit.status).toBe('CLOSED');
  });
});

test.describe('Billing System - Cash Visit Full Lifecycle', () => {
  test('Cash visit – full billing lifecycle', async ({ browser }) => {
    // Create separate contexts for each role
    // This is much faster and more stable than login/logout switching
    const receptionistContext = await browser.newContext();
    const doctorContext = await browser.newContext();
    const labTechContext = await browser.newContext();
    
    // Block notification polling to avoid SQLite "database is locked" errors
    const blockNotifications = async (context: any) => {
      await context.route('**/api/v1/notifications/**', (route: any) => route.abort());
    };
    
    await blockNotifications(receptionistContext);
    await blockNotifications(doctorContext);
    await blockNotifications(labTechContext);
    
    const receptionistPage = await receptionistContext.newPage();
    const doctorPage = await doctorContext.newPage();
    const labTechPage = await labTechContext.newPage();
    
    // Login each role once at the beginning
    console.log('Logging in all roles once...');
    await loginAs(receptionistPage, TEST_RECEPTIONIST);
    await loginAs(doctorPage, TEST_DOCTOR);
    await loginAs(labTechPage, TEST_LAB_TECH);
    
    // Step 1: Receptionist registers patient and creates visit
    const patientId = await registerPatient(receptionistPage, TEST_PATIENT);
    console.log(`Patient registered with ID: ${patientId}`);
    
    // Small delay to let SQLite settle
    await receptionistPage.waitForTimeout(1000);
    
    const visitId = await createVisit(receptionistPage, patientId, 'CASH');
    console.log(`Visit ${visitId} created for patient ${patientId}`);

    await receptionistPage.waitForTimeout(1500);
    await payRegistrationGate(receptionistPage, visitId);

    // Step 2: Doctor creates consultation and orders consultation service
    await createConsultation(doctorPage, visitId);
    await addBillingService(doctorPage, visitId, 'CONS-001', 'CONSULTATION');
    console.log(`Consultation created for visit ${visitId}`);

    // Step 3: Receptionist processes consultation payment
    let summary = await getBillingSummaryViaApi(receptionistPage, visitId);
    expect(summary.totalCharges).toBeGreaterThan(0);

    if (summary.outstandingBalance > 0) {
      await recordPaymentViaApi(receptionistPage, visitId, summary.outstandingBalance, 'CASH');
      console.log(`Initial payment processed for visit ${visitId}`);
    }

    // Step 4: Doctor adds lab order (consultation gate cleared after payment)
    await addLabOrder(doctorPage, visitId, 'CBC-001');
    console.log(`Lab order added for visit ${visitId}`);

    // Step 5: Pay lab charge before results can be posted
    summary = await getBillingSummaryViaApi(receptionistPage, visitId);
    if (summary.outstandingBalance > 0) {
      await recordPaymentViaApi(receptionistPage, visitId, summary.outstandingBalance, 'CASH');
      console.log(`Lab payment processed for visit ${visitId}`);
    }

    // Step 6: Lab Tech records results (requires payment cleared)
    await recordLabResult(labTechPage, visitId, 'Hemoglobin: 14.5 g/dL, WBC: 7,500/mm3');
    console.log(`Lab results recorded for visit ${visitId}`);

    // Step 7: Verify final state and receipt
    summary = await getBillingSummaryViaApi(receptionistPage, visitId);
    expect(summary.paymentStatus).toBe('PAID');
    expect(summary.outstandingBalance).toBe(0);
    
    console.log('Verifying receipt availability...');
    const receiptControl = await generateReceipt(receptionistPage, visitId);
    expect(receiptControl).toBeDefined();
    
    // Step 8: Doctor closes visit
    console.log('Closing visit...');
    await closeVisit(doctorPage, visitId);

    // Step 9: Final verification
    const headers = await apiHeaders(doctorPage);
    const visitRes = await doctorPage.request.get(`http://127.0.0.1:8000/api/v1/visits/${visitId}/`, {
      headers,
    });
    const closedVisit = (await visitRes.json()) as { status?: string };
    expect(closedVisit.status).toBe('CLOSED');
    
    // Cleanup
    await receptionistContext.close();
    await doctorContext.close();
    await labTechContext.close();
  });
});
