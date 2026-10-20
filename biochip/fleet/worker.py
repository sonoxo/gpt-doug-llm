"""Fixed one-request child, launched only by the local supervisor."""
from __future__ import annotations

from dataclasses import asdict
from http.client import HTTPException
from pathlib import Path
import sys

# -I excludes the working directory. Add only this installed source tree.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_killswitch import AIKillSwitchEngaged
from biochip.models import Model, ModelRouter, require_allowed
from biochip.validation import MAX_BYTES, bounded_int, decode_json, encode_json, finite_number


def main() -> int:
    try:
        require_allowed('Kraken worker admission')
        request = decode_json(sys.stdin.buffer.read(MAX_BYTES + 1))
        fields = {'provider', 'model', 'endpoint', 'prompt', 'system', 'max_tokens', 'timeout'}
        if not isinstance(request, dict) or request.keys() != fields:
            raise ValueError('invalid worker request fields')
        bounded_int(request['max_tokens'], name='max_tokens', minimum=1, maximum=1024)
        finite_number(request['timeout'], name='timeout', minimum=0, maximum=600, exclusive_minimum=True)
        model = Model(request['provider'], request['model'])
        router = ModelRouter({model.provider: request['endpoint']}, timeout=request['timeout'])
        models, errors = router.discover()
        if errors or model not in models:
            raise RuntimeError('selected model is not currently available')
        require_allowed('Kraken worker inference')
        result = router.chat_result(model, request['prompt'], system=request['system'], max_tokens=request['max_tokens'])
        require_allowed('Kraken worker reply')
        output, code = asdict(result), 0
    except AIKillSwitchEngaged:
        output, code = {'error': 'operator_stop'}, 3
    except (ValueError, TypeError):
        output, code = {'error': 'validation_failure'}, 2
    except (OSError, HTTPException, RuntimeError):
        output, code = {'error': 'provider_failure'}, 4
    try:
        sys.stdout.buffer.write(encode_json(output) + b'\n')
        sys.stdout.buffer.flush()
    except (OSError, ValueError):
        return 4
    return code


if __name__ == '__main__':
    raise SystemExit(main())
