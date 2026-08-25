import { createHash, createPrivateKey, createPublicKey, generateKeyPairSync, sign, verify } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';

export const COIN = 100_000_000n;
export const SYMBOL = 'XUN';
export const MAX_SUPPLY = 500_000_000n * COIN;
export const HALVING_INTERVAL = 210_000;
export const INITIAL_REWARD = 1_000n * COIN;
export const DEFAULT_DIFFICULTY = 3;

export const sha256 = (data: string | Buffer) => createHash('sha256').update(data).digest('hex');
export const addressFromPublicKey = (publicKeyPem: string) => {
  const der = createPublicKey(publicKeyPem).export({ type: 'spki', format: 'der' });
  return `xun_${sha256(der).slice(0, 40)}`;
};

export type SignedTransaction = {
  id: string;
  from: string;
  to: string;
  amount: string;
  fee: string;
  nonce: number;
  publicKey: string;
  signature: string;
  timestamp: number;
};

export const txPayload = (tx: Omit<SignedTransaction, 'id' | 'signature'>) => JSON.stringify({
  from: tx.from,
  to: tx.to,
  amount: tx.amount,
  fee: tx.fee,
  nonce: tx.nonce,
  publicKey: tx.publicKey,
  timestamp: tx.timestamp,
});

export class Wallet {
  readonly privateKey: string;
  readonly publicKey: string;
  readonly address: string;

  constructor(privateKey: string, publicKey: string) {
    this.privateKey = privateKey;
    this.publicKey = publicKey;
    this.address = addressFromPublicKey(publicKey);
  }

  static create() {
    const pair = generateKeyPairSync('ed25519');
    const privateKey = pair.privateKey.export({ type: 'pkcs8', format: 'pem' }).toString();
    const publicKey = pair.publicKey.export({ type: 'spki', format: 'pem' }).toString();
    return new Wallet(privateKey, publicKey);
  }

  static load(path: string) {
    const data = JSON.parse(readFileSync(path, 'utf8')) as { privateKey: string; publicKey: string };
    return new Wallet(data.privateKey, data.publicKey);
  }

  save(path: string) {
    writeFileSync(path, JSON.stringify({ address: this.address, privateKey: this.privateKey, publicKey: this.publicKey }, null, 2), { mode: 0o600 });
  }

  signPayment(to: string, amount: bigint, fee: bigint, nonce: number): SignedTransaction {
    const base = { from: this.address, to, amount: amount.toString(), fee: fee.toString(), nonce, publicKey: this.publicKey, timestamp: Date.now() };
    const signature = sign(null, Buffer.from(txPayload(base)), createPrivateKey(this.privateKey)).toString('base64');
    const id = sha256(`${txPayload(base)}:${signature}`);
    return { ...base, signature, id };
  }
}

export function verifyTransactionSignature(tx: SignedTransaction): boolean {
  try {
    if (addressFromPublicKey(tx.publicKey) !== tx.from) return false;
    const { id: _id, signature, ...base } = tx;
    if (sha256(`${txPayload(base)}:${signature}`) !== tx.id) return false;
    return verify(null, Buffer.from(txPayload(base)), createPublicKey(tx.publicKey), Buffer.from(signature, 'base64'));
  } catch {
    return false;
  }
}

export const blockReward = (height: number): bigint => {
  const halvings = Math.floor(height / HALVING_INTERVAL);
  if (halvings >= 64) return 0n;
  return INITIAL_REWARD >> BigInt(halvings);
};

export const parseXun = (value: string): bigint => {
  const match = value.trim().match(/^(\d+)(?:\.(\d{1,8}))?$/);
  if (!match) throw new Error('invalid XUN amount');
  const whole = BigInt(match[1]);
  const fraction = BigInt((match[2] ?? '').padEnd(8, '0'));
  return whole * COIN + fraction;
};

export const formatXun = (value: bigint) => `${value / COIN}.${(value % COIN).toString().padStart(8, '0')}`;
