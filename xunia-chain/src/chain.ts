import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { blockReward, DEFAULT_DIFFICULTY, MAX_SUPPLY, sha256, SignedTransaction, verifyTransactionSignature } from './crypto.js';

export type Block = {
  height: number;
  previousHash: string;
  timestamp: number;
  nonce: number;
  difficulty: number;
  miner: string;
  reward: string;
  transactions: SignedTransaction[];
  hash: string;
};

type ChainFile = { chainId: string; blocks: Block[] };

type AccountState = { balance: bigint; nonce: number };

const canonicalBlock = (block: Omit<Block, 'hash'>) => JSON.stringify({
  height: block.height,
  previousHash: block.previousHash,
  timestamp: block.timestamp,
  nonce: block.nonce,
  difficulty: block.difficulty,
  miner: block.miner,
  reward: block.reward,
  txids: block.transactions.map(t => t.id),
});

export class XuniaChain {
  readonly chainId = 'xunia-main-v1';
  readonly dataPath: string;
  blocks: Block[] = [];
  mempool: SignedTransaction[] = [];

  constructor(dataPath = '.xunia/chain.json') {
    this.dataPath = dataPath;
    if (existsSync(dataPath)) this.load();
    else {
      this.blocks = [this.genesis()];
      this.persist();
    }
    this.validateChain();
  }

  private genesis(): Block {
    const base = { height: 0, previousHash: '0'.repeat(64), timestamp: 1_788_000_000_000, nonce: 0, difficulty: 0, miner: 'genesis', reward: '0', transactions: [] as SignedTransaction[] };
    return { ...base, hash: sha256(canonicalBlock(base)) };
  }

  private load() {
    const parsed = JSON.parse(readFileSync(this.dataPath, 'utf8')) as ChainFile;
    if (parsed.chainId !== this.chainId) throw new Error('wrong chain id');
    this.blocks = parsed.blocks;
  }

  persist() {
    mkdirSync(dirname(this.dataPath), { recursive: true });
    writeFileSync(this.dataPath, JSON.stringify({ chainId: this.chainId, blocks: this.blocks }, null, 2));
  }

  tip() { return this.blocks[this.blocks.length - 1]; }

  totalIssued(): bigint {
    return this.blocks.reduce((sum, block) => sum + BigInt(block.reward), 0n);
  }

  stateAtTip(): Map<string, AccountState> {
    const state = new Map<string, AccountState>();
    for (const block of this.blocks.slice(1)) this.applyBlockToState(block, state, false);
    return state;
  }

  balance(address: string): bigint { return this.stateAtTip().get(address)?.balance ?? 0n; }
  nonce(address: string): number { return this.stateAtTip().get(address)?.nonce ?? 0; }

  submit(tx: SignedTransaction) {
    if (!verifyTransactionSignature(tx)) throw new Error('invalid transaction signature');
    if (tx.from === tx.to) throw new Error('self transfer rejected');
    if (!/^xun_[0-9a-f]{40}$/.test(tx.to)) throw new Error('invalid recipient address');
    const amount = BigInt(tx.amount);
    const fee = BigInt(tx.fee);
    if (amount <= 0n || fee < 0n) throw new Error('invalid amount or fee');
    if (this.mempool.some(existing => existing.id === tx.id)) throw new Error('duplicate transaction');
    const state = this.stateAtTip();
    for (const pending of this.mempool) this.applyTransaction(pending, state);
    this.applyTransaction(tx, state);
    this.mempool.push(tx);
    return tx.id;
  }

  mine(miner: string, difficulty = DEFAULT_DIFFICULTY): Block {
    if (!/^xun_[0-9a-f]{40}$/.test(miner)) throw new Error('invalid miner address');
    if (difficulty < 1 || difficulty > 6) throw new Error('difficulty out of range');
    const state = this.stateAtTip();
    const accepted: SignedTransaction[] = [];
    let fees = 0n;
    for (const tx of this.mempool) {
      try {
        this.applyTransaction(tx, state);
        fees += BigInt(tx.fee);
        accepted.push(tx);
      } catch { /* leave invalid/stale tx out */ }
    }
    const nextHeight = this.tip().height + 1;
    const scheduled = blockReward(nextHeight);
    const remaining = MAX_SUPPLY - this.totalIssued();
    const reward = scheduled > remaining ? remaining : scheduled;
    const target = '0'.repeat(difficulty);
    let nonce = 0;
    while (true) {
      const base = { height: nextHeight, previousHash: this.tip().hash, timestamp: Date.now(), nonce, difficulty, miner, reward: reward.toString(), transactions: accepted };
      const hash = sha256(canonicalBlock(base));
      if (hash.startsWith(target)) {
        const block: Block = { ...base, hash };
        this.blocks.push(block);
        this.mempool = this.mempool.filter(tx => !accepted.some(a => a.id === tx.id));
        this.persist();
        return block;
      }
      nonce++;
    }
  }

  private applyTransaction(tx: SignedTransaction, state: Map<string, AccountState>) {
    if (!verifyTransactionSignature(tx)) throw new Error('bad signature');
    const amount = BigInt(tx.amount), fee = BigInt(tx.fee);
    const sender = state.get(tx.from) ?? { balance: 0n, nonce: 0 };
    if (tx.nonce !== sender.nonce) throw new Error('bad nonce');
    if (sender.balance < amount + fee) throw new Error('insufficient funds');
    sender.balance -= amount + fee;
    sender.nonce++;
    state.set(tx.from, sender);
    const recipient = state.get(tx.to) ?? { balance: 0n, nonce: 0 };
    recipient.balance += amount;
    state.set(tx.to, recipient);
  }

  private applyBlockToState(block: Block, state: Map<string, AccountState>, verifyPow = true) {
    if (verifyPow && !block.hash.startsWith('0'.repeat(block.difficulty))) throw new Error('invalid proof of work');
    let fees = 0n;
    for (const tx of block.transactions) {
      this.applyTransaction(tx, state);
      fees += BigInt(tx.fee);
    }
    const miner = state.get(block.miner) ?? { balance: 0n, nonce: 0 };
    miner.balance += BigInt(block.reward) + fees;
    state.set(block.miner, miner);
  }

  validateChain() {
    const state = new Map<string, AccountState>();
    let issued = 0n;
    for (let i = 0; i < this.blocks.length; i++) {
      const block = this.blocks[i];
      const { hash, ...base } = block;
      if (sha256(canonicalBlock(base)) !== hash) throw new Error(`block ${i} hash mismatch`);
      if (i === 0) continue;
      const prev = this.blocks[i - 1];
      if (block.previousHash !== prev.hash || block.height !== prev.height + 1) throw new Error(`block ${i} linkage mismatch`);
      const scheduled = blockReward(block.height);
      issued += BigInt(block.reward);
      if (BigInt(block.reward) > scheduled || issued > MAX_SUPPLY) throw new Error(`block ${i} reward invalid`);
      this.applyBlockToState(block, state, true);
    }
    return true;
  }
}
