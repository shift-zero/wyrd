"""Run all tests and report results."""
import subprocess, sys, time

start = time.time()
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/', '-q', '--tb=short'],
    capture_output=True, text=True, timeout=250
)
elapsed = time.time() - start

print(f'Time: {elapsed:.1f}s')
print(f'Exit code: {result.returncode}')
print()
out = result.stdout
# Show last 2000 chars of output
if len(out) > 2000:
    print(out[-2000:])
else:
    print(out)
if result.stderr:
    print('STDERR:')
    print(result.stderr[-2000:])
