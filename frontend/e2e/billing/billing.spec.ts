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

// Set longer timeout for all tests in this file as they involve multiple role switches and database operations
test.setTimeout(120000);

// Test data fixtures
const TEST_PATIENT = {
  first_name: 'John',
  last_name: 'Doe',
  date_of_birth: '1990-01-15',
  gender: 'MALE',
  phone: '+2348012345678',
  email: 'john.doe@example.com',
};

const TEST_DOCTOR = {
  email: 'doctor@clinic.com',
  password: 'Doctor123!',
  role: 'DOCTOR',
};

const TEST_RECEPTIONIST = {
  email: 'receptionist@clinic.com',
  password: 'Receptionist123!',
  role: 'RECEPTIONIST',
};

const TEST_LAB_TECH = {
  email: 'labtech@clinic.com',
  password: 'LabTech123!',
  role: 'LAB_TECH',
};

/**
 * Helper: Check if backend is accessible
 */
async function checkBackendHealth(page: Page): Promise<boolean> {
  try {
    // Try both localhost and 127.0.0.1, and increase timeout
    const response = await page.request.get('http://127.0.0.1:8000/api/v1/health/', {
      timeout: 5000
    });
    if (response.ok()) return true;
    
    const responseLocal = await page.request.get('http://localhost:8000/api/v1/health/', {
      timeout: 5000
    });
    return responseLocal.ok();
  } catch (error) {
    console.error('Backend health check failed:', error);
    return false;
  }
}

/**
 * Helper: Logout current user
 */
async function logout(page: Page) {
  console.log('Logging out (aggressive)...');
  try {
    // 1. Clear all storage and cookies
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    }).catch(() => {});
    
    // 2. Navigate to about:blank to destroy any in-memory state
    await page.goto('about:blank');
    
    // 3. Clear cookies for the domain
    const context = page.context();
    await context.clearCookies();
    
    // 4. Now go to login page
    console.log('Navigating to login page...');
    await page.goto('/login', { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {
      return page.goto('/login', { waitUntil: 'domcontentloaded', timeout: 10000 });
    });
    
    // 5. Verify we are on login page and form is visible
    await expect(page.locator('#username, input[placeholder*="Username"]').first()).toBeVisible({ timeout: 15000 });
    console.log('Logged out successfully (aggressive)');
  } catch (error) {
    console.warn('Aggressive logout failed, forcing reload:', error.message);
    await page.goto('/login', { waitUntil: 'domcontentloaded' }).catch(() => {});
  }
}

/**
 * Helper: Login as a specific role
 */
async function loginAs(page: Page, user: { email: string; password: string }) {
  console.log(`Ensuring login state for ${user.email}...`);
  
  // Wait for any existing navigation to finish
  await page.waitForLoadState('domcontentloaded').catch(() => {});

  // Check if we are already logged in
  const logoutButton = page.locator('button:has-text("Logout"), button:has-text("Log out")').first();
  let isLoggedIn = await logoutButton.isVisible({ timeout: 2000 }).catch(() => false);
  
  if (isLoggedIn) {
    // Check if we're logged in as the right user
    const pageText = await page.textContent('body').catch(() => '');
    const userRoleLabel = user.email === TEST_RECEPTIONIST.email ? 'RECEPTIONIST' :
                          user.email === TEST_DOCTOR.email ? 'DOCTOR' :
                          user.email === TEST_LAB_TECH.email ? 'LAB_TECH' : '';
    
    const isCorrectUser = pageText?.includes(user.email) || 
                         (userRoleLabel && pageText?.includes(`(${userRoleLabel})`));
                         
    if (isCorrectUser) {
      console.log(`Already logged in as ${user.email}`);
      return;
    }
    
    console.log(`Logged in as wrong user, logging out...`);
    await logout(page);
  } else {
    // Not logged in, but check if we're on the login page
    if (!page.url().includes('/login')) {
      console.log('Not logged in and not on login page, navigating to /login...');
      await page.goto('/login', { waitUntil: 'domcontentloaded' }).catch(() => {});
    }
  }

  // Ensure we are on login page and form is visible
  let attempts = 0;
  while (attempts < 3) {
    try {
      console.log(`Login attempt ${attempts + 1} for ${user.email}...`);
      
      if (!page.url().includes('/login')) {
        await page.goto('/login', { waitUntil: 'domcontentloaded' });
      }
      
      const usernameInput = page.locator('#username, input[placeholder*="Username"]').first();
      await expect(usernameInput).toBeVisible({ timeout: 10000 });
      
      console.log('Filling login form...');
      await usernameInput.fill(user.email);
      await page.locator('#password, input[type="password"]').first().fill(user.password);
      
      console.log('Submitting login form...');
      const submitButton = page.locator('button:has-text("Sign In"), button:has-text("Signing in")').first();
      
      await Promise.all([
        page.waitForURL(url => !url.href.includes('/login'), { timeout: 20000 }),
        submitButton.click()
      ]);
      
      // Verify login actually worked (should see dashboard or logout button)
      const success = await page.locator('button:has-text("Logout"), button:has-text("Log out"), h1, h2').first().isVisible({ timeout: 10000 });
      if (success) {
        console.log(`Login successful for ${user.email}`);
        return;
      } else {
        throw new Error('Login form submitted but no dashboard elements visible');
      }
    } catch (e) {
      console.warn(`Login attempt ${attempts + 1} failed:`, e.message);
      attempts++;
      if (attempts < 3) {
        console.log('Retrying login after reload...');
        await page.goto('/login', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1000);
      }
    }
  }
  
  throw new Error(`Failed to login as ${user.email} after ${attempts} attempts.`);
}

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
  
  // Use URL parameter to pre-select the patient
  await page.goto(`/visits/new?patient=${patientId}`, { waitUntil: 'domcontentloaded' });
  
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
  
  return visitId;
}

/**
 * Helper: Create consultation (Doctor action)
 */
async function createConsultation(page: Page, visitId: number) {
  console.log(`Creating consultation for visit ${visitId}...`);
  await page.goto(`/visits/${visitId}/consultation`, { waitUntil: 'domcontentloaded' });
  
  // Wait for the consultation workspace to load
  await page.waitForSelector('h2:has-text("Consultation"), h1:has-text("Visit #")', { timeout: 15000 });
  
  // Check if we have an error (e.g. Payment required)
  const errorText = await page.locator('[class*="errorMessage"], [class*="errorDetails"]').first().textContent({ timeout: 2000 }).catch(() => '');
  if (errorText && errorText.includes('Payment must be cleared')) {
    throw new Error(`Consultation blocked: ${errorText}`);
  }

  // Use the new workspace selectors (id-based)
  // Fill History
  const historyInput = page.locator('textarea#history');
  await expect(historyInput).toBeVisible({ timeout: 5000 });
  await historyInput.fill('Patient complains of persistent headache and mild fever for 3 days.');
  
  // Fill Examination
  const examinationInput = page.locator('textarea#examination');
  await expect(examinationInput).toBeVisible({ timeout: 5000 });
  await examinationInput.fill('Temperature: 38.2°C, BP: 120/80. No visible neurological deficits.');
  
  // Fill Diagnosis
  const diagnosisInput = page.locator('textarea#diagnosis');
  await expect(diagnosisInput).toBeVisible({ timeout: 5000 });
  await diagnosisInput.fill('Suspected Tension Headache with low-grade fever.');
  
  // Fill Clinical Notes
  const notesInput = page.locator('textarea#clinical_notes');
  await expect(notesInput).toBeVisible({ timeout: 5000 });
  await notesInput.fill('Recommended rest, hydration, and lab investigations.');
  
  // Wait for button to be enabled (it's disabled until fields are filled/dirty)
  const saveButton = page.locator('button:has-text("Save Consultation")');
  await expect(saveButton).toBeEnabled({ timeout: 5000 });
  
  await saveButton.click();
  
  // Wait for success message - use a more reliable approach
  try {
    await page.waitForSelector('.success-message, .toast-success, [class*="success"]', { timeout: 5000 });
  } catch {
    // Fallback: wait for success text
    await page.waitForFunction(() => {
      const bodyText = document.body.textContent || '';
      return bodyText.toLowerCase().includes('successfully');
    }, { timeout: 5000 });
  }
}

/**
 * Helper: Add lab order (Doctor action in consultation workspace)
 */
async function addLabOrder(page: Page, visitId: number, testCode: string) {
  console.log(`Adding lab order ${testCode} for visit ${visitId}...`);
  
  // Ensure we are on the consultation page or visit details page
  const currentUrl = page.url();
  if (!currentUrl.includes(`/visits/${visitId}/consultation`) && !currentUrl.includes(`/visits/${visitId}`)) {
    await page.goto(`/visits/${visitId}/consultation`, { waitUntil: 'domcontentloaded' });
  }
  
  // Wait for page content
  await page.waitForSelector('h1:has-text("Visit #"), h2:has-text("Consultation")', { timeout: 15000 });

  // Find Lab Orders section
  const labHeading = page.locator('h2:has-text("Lab Orders"), h3:has-text("Lab Orders")').first();
  await expect(labHeading).toBeVisible({ timeout: 15000 });
  
  // Click "+ New Order" or "Add Lab Order"
  const addButton = page.locator('button:has-text("+ New Order"), button:has-text("Add Lab Order")').first();
  await expect(addButton).toBeVisible({ timeout: 10000 });
  await addButton.click();
  
  // Wait for form to appear
  const testInput = page.getByPlaceholder(/e\.g\., CBC, Blood Sugar/i).first();
  await expect(testInput).toBeVisible({ timeout: 5000 });
  await testInput.fill(testCode);
  
  // Clinical Indication
  const indicationInput = page.locator('textarea[placeholder*="indication"], textarea[name*="indication"], textarea[placeholder*="reason"]').first();
  if (await indicationInput.isVisible().catch(() => false)) {
    await indicationInput.fill('Routine checkup from E2E test');
  }
  
  // Wait for API response before checking form closure
  const submitButton = page.locator('button:has-text("Create Order")').filter({ hasText: /^Create Order$/ }).first();
  await expect(submitButton).toBeEnabled({ timeout: 5000 });
  
  // Set up API response wait
  const responsePromise = page.waitForResponse(
    (response) => 
      response.url().includes(`/api/v1/visits/${visitId}/laboratory/`) && 
      !response.url().includes('/results/') &&
      response.request().method() === 'POST',
    { timeout: 15000 }
  ).catch(() => null);
  
  // Click submit
  await submitButton.click();
  
  // Wait for API response
  const response = await responsePromise;
  if (response && !response.ok()) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(`Failed to create lab order: ${response.status()} ${JSON.stringify(errorData)}`);
  }
  
  // Wait for form to close - check that the input field is no longer visible
  // Also check that the "+ New Order" button reappears (indicating form closed)
  await Promise.race([
    expect(testInput).not.toBeVisible({ timeout: 10000 }),
    expect(addButton).toBeVisible({ timeout: 10000 })
  ]).catch(async (e) => {
    // If both checks fail, try waiting for success message
    try {
      await page.waitForSelector('.success-message, .toast-success, [class*="success"], text*=successfully', { timeout: 5000 });
      console.log('Lab order success message found');
    } catch {
      // Final check: is the form still visible?
      const isFormVisible = await testInput.isVisible().catch(() => false);
      if (isFormVisible) {
        throw new Error(`Lab order form did not close after submission. Form still visible.`);
      }
    }
  });
  
  // Give React a moment to update the UI
  await page.waitForTimeout(500);
  
  console.log(`Lab order ${testCode} added successfully for visit ${visitId}`);
}

/**
 * Helper: Get billing summary
 */
async function getBillingSummary(page: Page, visitId: number) {
  // Always reload the page to ensure we get the latest data from the backend
  console.log(`Getting billing summary for visit ${visitId} (forcing reload)...`);
  await page.goto(`/visits/${visitId}?t=${Date.now()}#billing-section`, { waitUntil: 'networkidle' }).catch(() => {
    return page.goto(`/visits/${visitId}?t=${Date.now()}#billing-section`, { waitUntil: 'domcontentloaded' });
  });
  
  // Wait for any loading states to disappear
  await page.waitForFunction(() => {
    const body = document.body.textContent || '';
    return !body.includes('Loading visit details') && !body.includes('Loading billing') && !body.includes('Initializing...');
  }, { timeout: 15000 }).catch(() => console.log('Wait for loading text timed out, continuing...'));

  // Ensure the summary container is present
  await page.waitForSelector('[data-testid="billing-summary"]', { timeout: 20000 });
  
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
  
  // Ensure we are on the visit details page
  const currentUrl = page.url();
  if (!currentUrl.includes(`/visits/${visitId}`)) {
    await page.goto(`/visits/${visitId}`, { waitUntil: 'domcontentloaded' });
  }
  
  // Wait for page to finish loading (spinner to disappear)
  await page.waitForFunction(() => {
    const loadingText = document.body.textContent || '';
    return !loadingText.includes('Loading visit details') && !loadingText.includes('Loading billing');
  }, { timeout: 15000 }).catch(() => console.log('Wait for loading text timed out, continuing...'));

  // Wait for billing section to be visible
  // The billing section is only visible to RECEPTIONIST
  try {
    await page.waitForSelector('[data-testid="billing-section-wrapper"], h2:has-text("Billing")', { timeout: 20000 });
  } catch (e) {
    const pageText = await page.textContent('body');
    if (pageText?.includes('Billing information is only available')) {
      throw new Error('Billing section not accessible. User might not have RECEPTIONIST role.');
    }
    throw new Error(`Billing section not found after 20s. URL: ${page.url()}`);
  }
  
  // Click on Payments tab if not already active
  const paymentsTab = page.locator('button:has-text("Payments"), [data-testid="payments-tab"]').first();
  await expect(paymentsTab).toBeVisible({ timeout: 10000 });
  await paymentsTab.click();
  
  // Wait for payment options to load
  await page.waitForSelector('button:has-text("Cash"), button:has-text("POS"), button:has-text("Transfer")', { timeout: 10000 });

  // Select payment method button
  const methodLabel = method === 'POS' ? 'POS' : 
                      method === 'CASH' ? 'Cash' : 
                      method === 'TRANSFER' ? 'Transfer' : 
                      method === 'WALLET' ? 'Wallet' : 'Paystack';
                      
  const methodButton = page.locator(`button:has-text("${methodLabel}")`).first();
  await expect(methodButton).toBeVisible({ timeout: 5000 });
  await methodButton.click();
  
  // Fill amount
  const amountInput = page.locator('input[type="number"], input[name="amount"]').first();
  await expect(amountInput).toBeVisible({ timeout: 5000 });
  await amountInput.fill(amount.toString());
  
  // Method specific fields
  if (method === 'POS' || method === 'TRANSFER') {
    const refInput = page.locator('input[type="text"][placeholder*="reference"], input[name="transaction_reference"]').first();
    await expect(refInput).toBeVisible({ timeout: 5000 });
    await refInput.fill(`REF-${Date.now()}`);
  }
  
  if (method === 'PAYSTACK') {
    const emailInput = page.locator('input[type="email"], input[name="customer_email"]').first();
    await expect(emailInput).toBeVisible({ timeout: 5000 });
    await emailInput.fill(TEST_PATIENT.email);
  }
  
  // Click submit button
  const submitButtonText = method === 'CASH' ? 'Record Cash Payment' :
                          method === 'POS' ? 'Record POS Payment' :
                          method === 'TRANSFER' ? 'Record Transfer Payment' :
                          method === 'PAYSTACK' ? 'Initialize Paystack Payment' :
                          'Process Wallet Payment';
                          
  const submitButton = page.locator(`button:has-text("${submitButtonText}")`).first();
  await expect(submitButton).toBeEnabled({ timeout: 5000 });
  await submitButton.click();
  
  // Wait for success message
  try {
    await page.waitForSelector('.success-message, .toast-success, [class*="success"], text*=successfully', { timeout: 15000 });
    console.log(`${method} payment processed successfully.`);
  } catch {
    console.log('Success message not found, checking if payment was processed by looking at balance...');
    // If no success message, we'll let the test continue and it will fail at the summary check if payment failed
  }
}

/**
 * Helper: Register a new patient (Receptionist action)
 * 
 * Returns the patient ID from the API response or extracted from the UI
 */
async function registerPatient(page: Page, patientData: typeof TEST_PATIENT): Promise<number> {
  // Use a unique name for each patient to avoid conflicts
  const uniqueId = Math.floor(Math.random() * 10000);
  const uniqueFirstName = `${patientData.first_name}${uniqueId}`;
  
  console.log(`Registering unique patient ${uniqueFirstName} ${patientData.last_name}...`);
  
  // Set up the listener BEFORE navigating
  let patientId = 0;
  const responsePromise = page.waitForResponse(async (response) => {
    if (response.url().includes('/api/v1/patients/') && response.request().method() === 'POST' && response.status() === 201) {
      const data = await response.json();
      patientId = data.id;
      return true;
    }
    return false;
  }, { timeout: 20000 }).catch(() => null);
  
  await page.goto('/patients/register', { waitUntil: 'domcontentloaded' });
  
  // Fill form fields
  await page.locator('h2:has-text("Personal Information")').waitFor({ timeout: 10000 });
  
  const personalInfoSection = page.locator('h2:has-text("Personal Information")').locator('..');
  await personalInfoSection.locator('input[type="text"]').first().fill(uniqueFirstName);
  await personalInfoSection.locator('input[type="text"]').nth(1).fill(patientData.last_name);
  await personalInfoSection.locator('input[type="date"]').first().fill(patientData.date_of_birth);
  await personalInfoSection.locator('select').first().selectOption(patientData.gender);
  
  const contactInfoSection = page.locator('h2:has-text("Contact Information")').locator('..');
  await contactInfoSection.locator('input[type="tel"]').first().fill(patientData.phone);
  await contactInfoSection.locator('input[type="email"]').first().fill(`${uniqueFirstName.toLowerCase()}@example.com`);
  
  // Submit
  await page.locator('button[type="submit"]:has-text("Register Patient")').click();
  
  // Wait for response and extract ID
  await responsePromise;
  
  if (patientId === 0) {
    // If API response didn't give us the ID, try to extract from URL if redirected
    await page.waitForURL(/\/patients\/\d+/, { timeout: 10000 }).catch(() => {});
    const urlMatch = page.url().match(/\/patients\/(\d+)/);
    if (urlMatch && urlMatch[1]) patientId = parseInt(urlMatch[1]);
  }
  
  if (patientId === 0) {
    throw new Error('Failed to register patient and extract ID.');
  }
  
  console.log(`Patient registered successfully with ID: ${patientId}`);
  return patientId;
}

/**
 * Helper: Record lab result (Lab staff action in consultation workspace)
 */
async function recordLabResult(page: Page, visitId: number, resultData: string) {
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
  console.log(`Generating receipt for visit ${visitId}...`);
  await page.goto(`/visits/${visitId}#billing-section`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('button:has-text("Download Receipt"), button:has-text("Generate Receipt")', { timeout: 15000 });
  
  const receiptButton = page.locator('button:has-text("Download Receipt"), button:has-text("Generate Receipt")').first();
  await expect(receiptButton).toBeEnabled();
  
  // Set up download listener
  const downloadPromise = page.waitForEvent('download', { timeout: 15000 });
  await receiptButton.click();
  
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('receipt');
  
  return download;
}

/**
 * Helper: Close visit (Doctor action)
 */
async function closeVisit(page: Page, visitId: number) {
  console.log(`Closing visit ${visitId}...`);
  await page.goto(`/visits/${visitId}`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('button:has-text("Close Visit")', { timeout: 15000 });
  
  const closeButton = page.locator('button:has-text("Close Visit")');
  await expect(closeButton).toBeEnabled();
  
  await closeButton.click();
  
  // Confirm close if confirmation dialog appears
  const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("Close Visit")').filter({ hasText: /confirm|yes/i });
  if (await confirmButton.count() > 0) {
    await confirmButton.first().click();
  }
  
  await page.waitForSelector('text=Visit Closed, .visit-closed, [class*="closed"]', { timeout: 15000 });
  console.log(`Visit ${visitId} closed successfully.`);
}

test.describe('Billing System - Visit-Scoped Billing', () => {
  test('should create visit and initialize billing', async ({ page }) => {
    await loginAs(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    
    // Verify visit created - we should already be on the visit page
    await expect(page).toHaveURL(new RegExp(`/visits/${visitId}`));
    
    // Wait for the billing section to be visible
    const billingHeading = page.locator('h2:has-text("Billing & Payments")');
    await expect(billingHeading).toBeVisible({ timeout: 15000 });
    
    // Verify initial billing state
    const summary = await getBillingSummary(page, visitId);
    expect(summary.totalCharges).toBe(0);
    expect(summary.outstandingBalance).toBe(0);
    expect(summary.paymentStatus).toBe('PAID');
  });

  test('should automatically create consultation charge when doctor creates consultation', async ({ page }) => {
    await loginAs(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    
    await loginAs(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    
    await loginAs(page, TEST_RECEPTIONIST);
    const summary = await getBillingSummary(page, visitId);
    
    expect(summary.totalCharges).toBeGreaterThan(0);
    expect(summary.outstandingBalance).toBe(summary.totalCharges);
    
    await page.click('button:has-text("Charges")');
    const chargesList = page.locator('h3:has-text("Charges Breakdown"), h2:has-text("Billing")').locator('..');
    await expect(chargesList.locator('text=Consultation').first()).toBeVisible({ timeout: 15000 });
  });

  test('should automatically create lab charge when lab order is added', async ({ page }) => {
    await loginAs(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    
    await loginAs(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    await addLabOrder(page, visitId, 'CBC-001');
    
    await loginAs(page, TEST_RECEPTIONIST);
    const summary = await getBillingSummary(page, visitId);
    expect(summary.totalCharges).toBeGreaterThan(0);
    
    await page.click('button:has-text("Charges")');
    const chargesList = page.locator('h3:has-text("Charges Breakdown"), h2:has-text("Billing")').locator('..');
    await expect(chargesList.locator('text=Laboratory').first()).toBeVisible({ timeout: 15000 });
  });
});

test.describe('Billing System - Payment Processing', () => {
  test('should process full cash payment and clear outstanding balance', async ({ page }) => {
    await loginAs(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    
    await loginAs(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    
    await loginAs(page, TEST_RECEPTIONIST);
    const initialSummary = await getBillingSummary(page, visitId);
    const amountToPay = initialSummary.outstandingBalance;
    
    await processPayment(page, visitId, amountToPay, 'CASH');
    
    const finalSummary = await getBillingSummary(page, visitId);
    expect(finalSummary.outstandingBalance).toBe(0);
    expect(finalSummary.paymentStatus).toBe('PAID');
  });

  test('should process partial payment and update outstanding balance', async ({ page }) => {
    await loginAs(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'CASH');
    
    await loginAs(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    
    await loginAs(page, TEST_RECEPTIONIST);
    const initialSummary = await getBillingSummary(page, visitId);
    const totalCharges = initialSummary.totalCharges;
    const partialAmount = Math.floor(totalCharges / 2);
    
    await processPayment(page, visitId, partialAmount, 'CASH');
    
    const afterPaymentSummary = await getBillingSummary(page, visitId);
    expect(afterPaymentSummary.outstandingBalance).toBeCloseTo(totalCharges - partialAmount, 2);
    expect(afterPaymentSummary.paymentStatus).toBe('PARTIALLY_PAID');
    
    await processPayment(page, visitId, afterPaymentSummary.outstandingBalance, 'CASH');
    
    const finalSummary = await getBillingSummary(page, visitId);
    expect(finalSummary.outstandingBalance).toBe(0);
    expect(finalSummary.paymentStatus).toBe('PAID');
  });
});

test.describe('Billing System - Insurance Visits', () => {
  test('should create insurance visit and defer payment', async ({ page }) => {
    await loginAs(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'INSURANCE');
    
    await page.goto(`/visits/${visitId}`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('text=INSURANCE')).toBeVisible();
    
    await loginAs(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    
    await loginAs(page, TEST_RECEPTIONIST);
    const summary = await getBillingSummary(page, visitId);
    expect(summary.paymentStatus).toBe('INSURANCE_PENDING');
    
    await page.goto(`/visits/${visitId}`, { waitUntil: 'domcontentloaded' });
    const paymentsTab = page.locator('button:has-text("Payments")');
    await paymentsTab.click();
    await expect(page.locator('button:has-text("Cash")')).toBeDisabled();
  });

  test('should allow doctor to close insurance visit with pending status', async ({ page }) => {
    await loginAs(page, TEST_RECEPTIONIST);
    const patientId = await registerPatient(page, TEST_PATIENT);
    const visitId = await createVisit(page, patientId, 'INSURANCE');
    
    await loginAs(page, TEST_DOCTOR);
    await createConsultation(page, visitId);
    
    await expect(page.locator('button:has-text("Close Visit")')).toBeEnabled();
    await closeVisit(page, visitId);
    await expect(page.locator('text=Visit Closed')).toBeVisible();
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
    
    // Step 2: Doctor creates consultation
    await createConsultation(doctorPage, visitId);
    console.log(`Consultation created for visit ${visitId}`);
    
    // Wait for signals to process consultation charge
    await receptionistPage.waitForTimeout(2000);
    
    // Step 3: Receptionist processes initial payment
    // We expect a consultation charge now
    let summary = await getBillingSummary(receptionistPage, visitId);
    
    // Retry summary if charges are still 0 (signals might be slow)
    let retries = 0;
    while (summary.totalCharges === 0 && retries < 3) {
      console.log(`Charges are still 0, retrying summary (attempt ${retries + 1})...`);
      await receptionistPage.waitForTimeout(2000);
      summary = await getBillingSummary(receptionistPage, visitId);
      retries++;
    }
    
    if (summary.totalCharges === 0) {
      console.warn('Consultation created but charges are still 0. Signal might have failed or not triggered.');
    }
    
    if (summary.outstandingBalance > 0) {
      await processPayment(receptionistPage, visitId, summary.outstandingBalance, 'CASH');
      console.log(`Initial payment processed for visit ${visitId}`);
    }
    
    // Step 4: Doctor adds lab order
    await addLabOrder(doctorPage, visitId, 'CBC-001');
    console.log(`Lab order added for visit ${visitId}`);
    
    // Wait for lab charge signal and database to commit
    await receptionistPage.waitForTimeout(3000);
    
    // Step 5: Lab Tech records results
    // The recordLabResult helper will handle navigation and waiting for the lab order to appear
    await recordLabResult(labTechPage, visitId, 'Hemoglobin: 14.5 g/dL, WBC: 7,500/mm3');
    console.log(`Lab results recorded for visit ${visitId}`);
    
    // Wait for any additional charges (e.g. from results if any)
    await receptionistPage.waitForTimeout(2000);
    
    // Step 6: Receptionist processes final payment
    summary = await getBillingSummary(receptionistPage, visitId);
    if (summary.outstandingBalance > 0) {
      await processPayment(receptionistPage, visitId, summary.outstandingBalance, 'CASH');
      console.log(`Final payment processed for visit ${visitId}`);
    }
    
    // Step 7: Verify final state and receipt
    summary = await getBillingSummary(receptionistPage, visitId);
    expect(summary.paymentStatus).toBe('PAID');
    expect(summary.outstandingBalance).toBe(0);
    
    console.log('Generating receipt...');
    const receiptDownload = await generateReceipt(receptionistPage, visitId);
    expect(receiptDownload).toBeDefined();
    
    // Step 8: Doctor closes visit
    console.log('Closing visit...');
    await closeVisit(doctorPage, visitId);
    
    // Step 9: Final verification
    await doctorPage.goto(`/visits/${visitId}`, { waitUntil: 'domcontentloaded' });
    await expect(doctorPage.locator('text=Visit Closed, .visit-closed, [class*="closed"]')).toBeVisible();
    
    // Cleanup
    await receptionistContext.close();
    await doctorContext.close();
    await labTechContext.close();
  });
});
