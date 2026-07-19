import { Page } from '@playwright/test';

export async function apiHeaders(page: Page) {
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

export async function addBillingService(
  page: Page,
  visitId: number,
  serviceCode: string,
  department: string,
  additionalData?: Record<string, unknown>
) {
  const headers = await apiHeaders(page);
  let lastError = `add-item ${serviceCode} failed`;

  const payload: Record<string, unknown> = {
    visit_id: visitId,
    department,
    service_code: serviceCode,
  };
  if (additionalData) {
    payload.additional_data = additionalData;
  }

  for (let attempt = 0; attempt < 4; attempt++) {
    const res = await page.request.post('http://127.0.0.1:8000/api/v1/billing/add-item/', {
      headers,
      data: payload,
    });

    if (res.ok()) return;

    const body = await res.json().catch(() => ({}));
    const msg = JSON.stringify(body);
    lastError = `add-item ${serviceCode} failed (${res.status()}): ${msg}`;

    if (msg.toLowerCase().includes('already exists')) return;

    if (msg.toLowerCase().includes('database is locked') && attempt < 3) {
      await page.waitForTimeout(1500 * (attempt + 1));
      continue;
    }
    break;
  }

  throw new Error(lastError);
}

export async function getBillingSummaryViaApi(page: Page, visitId: number) {
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
      return {
        totalCharges: parseFloat(String(data.total_charges ?? '0')),
        outstandingBalance: parseFloat(String(data.outstanding_balance ?? '0')),
        paymentStatus: (data.payment_status ?? '').trim(),
      };
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

export async function recordPaymentViaApi(
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

/** Pay REG-001 so doctor can open the consultation workspace. */
export async function payRegistrationGate(
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
