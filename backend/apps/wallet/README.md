# Wallet System

## Overview

The wallet system provides patients with a digital wallet for managing payments. Each patient automatically gets a wallet when their account is created.

## Features

- **Auto-created wallets**: Every patient gets a wallet automatically
- **Multiple payment channels**: Paystack, Mobile Money, Bank Transfer, Cash, Card, Insurance
- **Transaction history**: Immutable transaction records
- **Visit payments**: Pay for visits directly from wallet
- **Top-up functionality**: Add funds via Paystack or other channels

## Models

### Wallet
- One-to-one relationship with Patient
- Tracks balance and currency
- Auto-created via signal when patient is created

### PaymentChannel
- Configurable payment channels (Paystack, Mobile Money, etc.)
- Channel-specific configuration stored in JSON field

### WalletTransaction
- Immutable transaction records
- Tracks credits, debits, and balance changes
- Links to visits when applicable
- Stores gateway transaction IDs

## API Endpoints

### Wallets
- `GET /api/v1/wallet/wallets/` - List wallets (filtered by role)
- `GET /api/v1/wallet/wallets/{id}/` - Get wallet details
- `GET /api/v1/wallet/wallets/{id}/transactions/` - Get transaction history
- `POST /api/v1/wallet/wallets/{id}/top-up/` - Top up wallet
- `POST /api/v1/wallet/wallets/{id}/verify-payment/` - Verify payment after gateway callback
- `POST /api/v1/wallet/wallets/{id}/pay-visit/` - Pay for visit using wallet

### Payment Channels
- `GET /api/v1/wallet/payment-channels/` - List active payment channels

## Setup

1. **Install dependencies**:
   ```bash
   pip install requests
   ```

2. **Set environment variables**:
   ```bash
   PAYSTACK_SECRET_KEY=sk_test_...
   PAYSTACK_PUBLIC_KEY=pk_test_...
   PAYSTACK_CALLBACK_URL=http://localhost:3001/wallet/callback
   ```

3. **Run migrations**:
   ```bash
   python manage.py migrate wallet
   ```

4. **Set up payment channels**:
   ```bash
   python manage.py setup_payment_channels
   ```

## Usage

### For Patients

1. **View wallet**: Navigate to `/wallet`
2. **Top up**: Click "Top Up Wallet", enter amount, select payment method
3. **Pay for visit**: On visit details page, click "Pay with Wallet" button

### For Receptionists

- Can view all patient wallets
- Can see transaction history
- Wallet payments automatically create Payment records and update visit status

## Payment Flow

1. Patient initiates top-up → Gateway redirects to Paystack
2. Patient completes payment → Paystack redirects to callback URL
3. Backend verifies payment → Updates wallet balance
4. Transaction recorded → Immutable audit trail

## Security

- All transactions are immutable (append-only)
- Full audit logging for compliance
- Role-based access control
- Payment verification before wallet credit

## Integration with Existing Payment System

- Wallet payments create `Payment` records in the billing app
- Visit payment status automatically updated to CLEARED
- All EMR rules enforced (visit-scoped, audit logs, etc.)
