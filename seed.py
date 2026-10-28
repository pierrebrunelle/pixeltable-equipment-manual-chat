"""Load the demo manuals and ask a few questions.

Cost: one embedding call per chunk batch plus, per question, one embedding call and one
gpt-4o-mini call.

    python make_manuals.py    # writes data/manuals/
    python seed.py            # local catalog 'manuals'
    python seed.py pxt://<your-org>:<your-db>
"""

from __future__ import annotations

import sys
from pathlib import Path

from app import Chunks, Manuals, Questions, TableModel

TARGET = sys.argv[1] if len(sys.argv) > 1 else 'manuals'
HERE = Path(__file__).parent / 'data' / 'manuals'

MANUALS = [
    {'manual_id': 'hl300-scissor-lift', 'equipment': 'HydraLift HL-300 scissor lift', 'vendor': 'HydraLift', 'doc': HERE / 'hl300-scissor-lift.pdf'},
    {'manual_id': 'kr48-cnc-router', 'equipment': 'Kestrel KR-48 CNC router', 'vendor': 'Kestrel', 'doc': HERE / 'kr48-cnc-router.pdf'},
    {'manual_id': 'bw90-dishwasher', 'equipment': 'Brightwave BW-90 dishwasher', 'vendor': 'Brightwave', 'doc': HERE / 'bw90-dishwasher.pdf'},
    {'manual_id': 'af60-air-compressor', 'equipment': 'AeroFlow AF-60 compressor', 'vendor': 'AeroFlow', 'doc': HERE / 'af60-air-compressor.pdf'},
    {'manual_id': 'rc14-freezer', 'equipment': 'FrostLine RC-14 freezer', 'vendor': 'FrostLine', 'doc': HERE / 'rc14-freezer.md'},
]

QUESTIONS = [
    {'question': 'The scissor lift shows E12. What does it mean and what do I do?', 'equipment': 'HydraLift HL-300 scissor lift', 'asked_by': 'night-shift'},
    {'question': 'How often do I grease the linear bearings on the CNC router, and with what?', 'equipment': None, 'asked_by': 'shop'},
    {'question': 'What final rinse temperature does the dishwasher need?', 'equipment': None, 'asked_by': 'kitchen'},
    {'question': 'Which filters are replaced at 2000 hours on the compressor?', 'equipment': None, 'asked_by': 'facilities'},
    {'question': 'What is the warranty period of the freezer?', 'equipment': None, 'asked_by': 'kitchen'},  # not in the manuals
]

if __name__ == '__main__':
    TableModel.bind_all(TARGET)
    print(Manuals.insert([{**m, 'doc': str(m['doc'])} for m in MANUALS], on_error='ignore'))
    print('chunks:', Chunks.count())
    print(Questions.insert(QUESTIONS, on_error='ignore'))
    for row in Questions.select(Questions.question, Questions.answer).collect():
        print('-', row['question'], '\n ', row['answer'])
