import { PaymentChannel } from '../types/wallet';

const ONLINE_TOP_UP_CHANNEL_TYPES = new Set(['PAYSTACK', 'CARD']);

export function getOnlineTopUpChannels(channels: PaymentChannel[]): PaymentChannel[] {
  return channels.filter(
    (channel) =>
      channel.is_active &&
      (channel.supports_online_topup === true ||
        ONLINE_TOP_UP_CHANNEL_TYPES.has(channel.channel_type)),
  );
}

export function pickDefaultTopUpChannelId(channels: PaymentChannel[]): number | null {
  const onlineChannels = getOnlineTopUpChannels(channels);
  if (onlineChannels.length === 0) {
    return null;
  }

  const paystack =
    onlineChannels.find((channel) => channel.channel_type === 'PAYSTACK') ??
    onlineChannels.find((channel) => channel.name.toLowerCase().includes('paystack'));

  return (paystack ?? onlineChannels[0]).id;
}

export function getPaymentChannelLabel(channel: PaymentChannel): string {
  const description = channel.config?.description;
  if (typeof description === 'string' && description.trim()) {
    return `${channel.name} — ${description}`;
  }
  return channel.name;
}

export function parsePaymentChannelId(value: string): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}
