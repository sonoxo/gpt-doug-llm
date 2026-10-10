"""Interactive local Cure Swarm evidence console; synthetic demo until explicit online CLI."""
from __future__ import annotations

import argparse
import sys

from research_lab import cure_swarm


def dashboard() -> None:
    report = cure_swarm.analyze(cure_swarm.sample_snapshot())
    print('='*65)
    print(' BIO-GPT / CURE SWARM        ONCOLOGY RESEARCH CONSOLE')
    print('='*65)
    print(' OFFLINE | SIMULATED EVIDENCE | HUMAN SCIENTIFIC REVIEW REQUIRED')
    print(' Real cures discovered: NONE. No treatments recommended.')
    print(' Public API connections: OFF (explicit online command required)')
    print(' Registered simulated studies:', report['counts']['studies'])
    print(' Simulated publications:       ', report['counts']['publications'])
    print(' Five research roles:           available as bounded code stages')
    print()


def agents() -> None:
    report = cure_swarm.analyze(cure_swarm.sample_snapshot())
    print('\nRESEARCH ROLES (NO BACKGROUND AGENTS LAUNCHED)')
    for stage in report['agents']:
        print(f" {stage['role']:<23} {stage['function']}")
    print(' Safety: no diagnoses, treatments, doses, or clinical action.\n')


def gaps() -> None:
    report = cure_swarm.analyze(cure_swarm.sample_snapshot())
    print('\nEVIDENCE REVIEW QUEUE (ALL SIMULATED, NO REAL PATIENTS)')
    for row in report['evidence']:
        print(' ', row['id'], '->', ', '.join(row['review_flags']))
    print(' Full clinical assessment must be performed by qualified researchers.\n')


def verify() -> None:
    report = cure_swarm.analyze(cure_swarm.sample_snapshot())
    print('\nPROVENANCE REPLAY:', 'VERIFIED' if cure_swarm.verify(report) else 'INVALID')
    print(' Evidence digest:',report['report_sha256'])
    print(' Hashes confirm internal consistency, NOT efficacy or authenticity.\n')


def open_console() -> int:
    dashboard()
    while True:
        print('[1] View synthetic research dashboard')
        print('[2] Inspect five research agents')
        print('[3] Examine evidence-review gaps')
        print('[4] Verify internal evidence report')
        print('[q] Quit Cure Swarm')
        try:
            answer=input('Cure-Swarm> ').strip().lower()
        except EOFError:
            print('\nInput closed. No background workers remain.')
            return 0
        except KeyboardInterrupt:
            print('\nInterrupted by operator.')
            return 130
        if answer in ('1','demo','dashboard'):
            dashboard()
        elif answer in ('2','agents'):
            agents()
        elif answer in ('3','gaps'):
            gaps()
        elif answer in ('4','verify'):
            verify()
        elif answer in ('q','exit','quit','0'):
            print('Cure Swarm stopped. No background workers remain.')
            return 0
        else:
            print('Invalid selection. Choose 1,2,3,4 or q.\n')


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once',action='store_true',help='print an offline dashboard and exit')
    args=parser.parse_args(argv)
    if args.once:
        dashboard()
        return 0
    return open_console()


if __name__=='__main__':
    sys.exit(main())
