import json

canon = json.load(open('ruckus_canon.json'))
entries = sorted(canon['entries'], key=lambda x: x.get('score', 0), reverse=True)
print(f'Total canon entries: {len(entries)}')
print()
for e in entries[:20]:
    print(f"Score {e['score']} | {e['text'][:100]}")
    print(f"Crack: {e.get('crack','')[:80]}")
    print()