import { existsSync } from 'node:fs';
import { XuniaChain } from './chain.js';
import { formatXun, parseXun, Wallet } from './crypto.js';

const [, , cmd, ...args] = process.argv;
const dataPath = process.env.XUNIA_DATA ?? '.xunia/chain.json';
const walletPath = process.env.XUNIA_WALLET ?? '.xunia/wallet.json';
const rpc = process.env.XUNIA_RPC ?? 'http://127.0.0.1:4317';

const requireWallet = () => {
  if (!existsSync(walletPath)) throw new Error(`wallet not found: ${walletPath}; run wallet first`);
  return Wallet.load(walletPath);
};

switch (cmd) {
  case 'wallet': {
    const wallet = Wallet.create();
    wallet.save(walletPath);
    console.log(wallet.address);
    break;
  }
  case 'balance': {
    const address = args[0] ?? requireWallet().address;
    const response = await fetch(`${rpc}/balance/${encodeURIComponent(address)}`);
    if (!response.ok) throw new Error(`node rejected balance request: ${response.status}`);
    const body = await response.json() as { xun: string };
    console.log(`${body.xun} XUN`);
    break;
  }
  case 'mine': {
    const wallet = requireWallet();
    const difficulty = args[0] ? Number(args[0]) : undefined;
    const response = await fetch(`${rpc}/mine`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ miner: wallet.address, difficulty }) });
    if (!response.ok) throw new Error(`node rejected mine request: ${await response.text()}`);
    console.log(JSON.stringify(await response.json(), null, 2));
    break;
  }
  case 'send': {
    const wallet = requireWallet();
    const [to, amountText, feeText = '0.00010000'] = args;
    if (!to || !amountText) throw new Error('usage: send <xun_address> <amount> [fee]');
    const balanceResponse = await fetch(`${rpc}/balance/${encodeURIComponent(wallet.address)}`);
    if (!balanceResponse.ok) throw new Error(`node unavailable: ${balanceResponse.status}`);
    const account = await balanceResponse.json() as { nonce: number };
    const tx = wallet.signPayment(to, parseXun(amountText), parseXun(feeText), account.nonce);
    const response = await fetch(`${rpc}/tx`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(tx) });
    if (!response.ok) throw new Error(`node rejected transaction: ${await response.text()}`);
    console.log(JSON.stringify(await response.json(), null, 2));
    break;
  }
  case 'offline-balance': {
    const chain = new XuniaChain(dataPath);
    const address = args[0] ?? requireWallet().address;
    console.log(`${formatXun(chain.balance(address))} XUN`);
    break;
  }
  default:
    console.log('XUNIA CLI\n  wallet\n  balance [address]\n  mine [difficulty]\n  send <address> <amount> [fee]\n  offline-balance [address]');
}
