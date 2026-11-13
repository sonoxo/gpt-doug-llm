#!/usr/bin/env python3
"""GPT-DOUG bounded, authorized, multi-host evidence crawler swarm.

Stdlib only. Reuses the existing XUNIA web mirror's SSRF, robots, redirect,
noindex and private-path controls. Does not authenticate or perform actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import xunia_authorized_crawl as guard
import xunia_web_mirror as mirror

SCHEMA = 'gpt-doug.crawler-swarm.v1'
MAX_HOSTS = 12
MAX_WORKERS = 4
MAX_PAGES_PER_HOST = 12
MAX_TOTAL_PAGES = 96
ID_PATTERN = re.compile(r'^[a-z][a-z0-9_-]{0,39}$')


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_manifest(path):
    p = Path(path)
    if not p.is_file() or p.stat().st_size > 65536:
        raise ValueError('Manifest must be a JSON file of 64 KiB or less')
    try:
        config = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Cannot read valid JSON manifest') from exc
    return validate_manifest(config)


def validate_manifest(config):
    if not isinstance(config, dict) or config.get('schema') != SCHEMA:
        raise ValueError('Unsupported manifest schema')
    targets = config.get('targets')
    if not isinstance(targets, list) or not 1 <= len(targets) <= MAX_HOSTS:
        raise ValueError('Targets must include 1-12 explicitly approved hosts')
    ids, hosts, result = set(), set(), []
    for row in targets:
        if not isinstance(row, dict):
            raise ValueError('Each target must be an object')
        ident, url, host = row.get('id'), row.get('base_url'), row.get('allow_host')
        if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident) or ident in ids:
            raise ValueError('Duplicate or invalid target id')
        if not isinstance(host, str) or not host or host != host.lower() or host in hosts:
            raise ValueError('Hosts must be unique lowercase exact hostnames')
        if not isinstance(url, str) or len(url) > 2048:
            raise ValueError('Invalid seed URL')
        try:
            parsed = urlsplit(url)
            if parsed.query or parsed.fragment or url != mirror.normalize_url(url, host):
                raise ValueError('Seed may not contain queries, fragments or restricted paths')
        except (ValueError, AttributeError) as exc:
            raise ValueError('Seed must be an allowlisted public HTTPS page') from exc
        if not guard.allowed_url(url, host):
            raise ValueError('Seed must be an exact-host HTTPS page')
        pages = row.get('max_pages', 6)
        depth = row.get('max_depth', 1)
        if type(pages) is not int or not 1 <= pages <= MAX_PAGES_PER_HOST:
            raise ValueError('max_pages must be 1-12 per host')
        if type(depth) is not int or not 0 <= depth <= 2:
            raise ValueError('max_depth must be 0-2')
        if row.get('authorized') is not True:
            raise ValueError('Every target needs explicit authorized: true')
        ids.add(ident)
        hosts.add(host)
        result.append({'id': ident, 'base_url': url, 'allow_host': host,
                       'max_pages': pages, 'max_depth': depth})
    if sum(row['max_pages'] for row in result) > MAX_TOTAL_PAGES:
        raise ValueError('Total page budget exceeds 96')
    return result


def index_page(page, source_id):
    """Metadata-only, neural-ready evidence; never copy body text to output."""
    title = page.get('title', '')
    url = page['url']
    digest = page['sha256']
    return {'id': hashlib.sha256(f'{source_id}\n{url}\n{digest}'.encode()).hexdigest(),
            'kind': 'public_web_evidence', 'source_id': source_id,
            'url': url, 'title': title, 'sha256': digest,
            'bytes': page['bytes'], 'depth': page['depth'],
            'observed_at': page['observedAt'],
            'neural_features': {'title_word_count': min(64, len(title.split())),
                                'document_kib': round(min(500, page['bytes']) / 1024, 4),
                                'link_depth': page['depth']},
            'classification': 'public_unverified'}


def crawl_target(target, *, mirror_fn=mirror.mirror):
    host = target['allow_host']
    try:
        snapshot = mirror_fn(target['base_url'], host, target['max_pages'],
                             target['max_depth'], 2.0, 8.0)
        evidence = [index_page(p, target['id']) for p in snapshot['pages']]
        return {'id': target['id'], 'host': host, 'status': 'completed',
                'coverage': snapshot['coverage'], 'evidence': evidence,
                'edges': snapshot['edges'], 'outbound_domains': snapshot['outboundDomains']}
    except Exception as exc:
        # Prevent leaking URLs/headers/secrets in third-party exception text.
        return {'id': target['id'], 'host': host, 'status': 'failed',
                'error_type': type(exc).__name__, 'coverage': {},
                'evidence': [], 'edges': [], 'outbound_domains': []}


def run_swarm(targets, workers=3, *, crawl_fn=crawl_target):
    if type(workers) is not int or not 1 <= workers <= MAX_WORKERS:
        raise ValueError('workers must be 1-4')
    if not targets:
        raise ValueError('No targets')
    # Each host is unique and appears in only one worker; no per-host concurrency.
    ordered = [None] * len(targets)
    with ThreadPoolExecutor(max_workers=min(workers, len(targets))) as pool:
        submitted = {pool.submit(crawl_fn, row): i for i, row in enumerate(targets)}
        for done in as_completed(submitted):
            i = submitted[done]
            try:
                ordered[i] = done.result()
            except Exception as exc:
                ordered[i] = {'id': targets[i]['id'], 'host': targets[i]['allow_host'],
                              'status': 'failed', 'error_type': type(exc).__name__,
                              'coverage': {}, 'evidence': [], 'edges': [], 'outbound_domains': []}
    records = [item for item in ordered if item is not None]
    return {'schema': SCHEMA, 'mode': 'authorized-public-web-metadata',
            'generated_at': utc_now(), 'synthetic': False,
            'policy': {'authorized_hosts_only': True, 'robots_txt': True,
                       'noindex_nofollow': True, 'credentialed_access': False,
                       'automatic_actions': False, 'raw_page_text_exported': False,
                       'limit_workers': MAX_WORKERS, 'per_host_delay_seconds': 2},
            'summary': {'targets': len(records),
                        'completed': sum(r['status'] == 'completed' for r in records),
                        'failed': sum(r['status'] == 'failed' for r in records),
                        'evidence_records': sum(len(r['evidence']) for r in records)},
            'targets': records}


def write_atomic(path, data):
    dest = Path(path).expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.crawler-swarm-', suffix='.tmp', dir=dest.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def demo():
    sample = {'schema': SCHEMA, 'mode': 'offline-synthetic-demo',
              'generated_at': utc_now(), 'synthetic': True,
              'policy': {'network_requests': False, 'automatic_actions': False},
              'summary': {'targets': 1, 'completed': 1, 'failed': 0, 'evidence_records': 1},
              'targets': [{'id': 'demo', 'host': 'example.org', 'status': 'completed',
                           'coverage': {'pagesStored': 1, 'pagesVisited': 1},
                           'evidence': [{'id': 'synthetic', 'kind': 'public_web_evidence',
                                         'source_id': 'demo', 'url': 'https://example.org/',
                                         'title': 'Synthetic evidence sample', 'sha256': 'synthetic',
                                         'classification': 'synthetic'}],
                           'edges': [], 'outbound_domains': []}]}
    return sample


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--manifest', type=Path, help='Explicit per-host authorization manifest')
    choice.add_argument('--demo', action='store_true', help='Offline synthetic example, no web requests')
    parser.add_argument('--authorized', action='store_true', help='Affirm ownership or crawl permission')
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--out', type=Path, default=Path('crawler-swarm-evidence.json'))
    args = parser.parse_args(argv)
    if args.manifest is not None and not args.authorized:
        parser.error('Real crawls require --authorized and approved targets in the manifest')
    try:
        data = demo() if args.demo else run_swarm(read_manifest(args.manifest), args.workers)
        write_atomic(args.out, data)
        print(f'KRAKEN SWARM: {data["summary"]["evidence_records"]} evidence records; '
              f'{data["summary"]["failed"]} failed hosts; saved {args.out}')
        return 0 if data['summary']['failed'] == 0 else 1
    except (OSError, ValueError) as exc:
        print('CRAWLER SWARM BLOCKED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
