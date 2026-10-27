"""Write the demo equipment manuals into data/manuals/ (4 PDFs + 1 Markdown file).

The manuals are small but realistic: safety notes, specifications, a maintenance schedule and a
fault-code table per machine, with concrete numbers the chat API can be checked against.

    python make_manuals.py
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

OUT = Path(__file__).parent / 'data' / 'manuals'

MANUALS = {
    'hl300-scissor-lift': (
        'HydraLift HL-300 Scissor Lift - Operator Manual',
        [
            ('1. Safety', [
                'Never raise the platform on a slope steeper than 2 degrees; the tilt alarm sounds at 1.5 degrees and lift-up is disabled at 2 degrees.',
                'Maximum platform load is 300 kg including two occupants. The overload sensor blocks lift-up above 330 kg.',
                'Do not operate outdoors in wind gusts above 12.5 m/s (28 mph).',
            ]),
            ('2. Specifications', [
                'Maximum working height 9.8 m; maximum platform height 7.8 m; stowed height 2.1 m.',
                'Batteries: four 6 V 225 Ah deep-cycle batteries (24 V system). A full charge takes 8 hours on the onboard 25 A charger.',
                'Drive speed: 3.5 km/h stowed, 0.8 km/h with the platform raised.',
            ]),
            ('3. Maintenance schedule', [
                'Daily: check hydraulic oil level with the platform fully lowered; it must reach the FULL mark on the dipstick.',
                'Every 250 hours: replace the hydraulic return filter (part HL-F250).',
                'Every 1000 hours or yearly: replace the hydraulic oil (ISO VG 32, 19 litres) and inspect the scissor pins for wear above 0.5 mm.',
            ]),
            ('4. Fault codes', [
                'E01 - Tilt alarm: the chassis is more than 1.5 degrees off level. Move the machine to level ground and lower the platform.',
                'E07 - Overload: the platform load exceeds 330 kg. Remove material until the alarm clears.',
                'E12 - Low battery voltage below 21.6 V: lift-up is disabled; drive to a charger and charge for 8 hours.',
                'E18 - Pothole guard did not deploy: check the guard linkage for debris; the machine will not drive with the platform raised until it clears.',
            ]),
        ],
    ),
    'kr48-cnc-router': (
        'Kestrel KR-48 CNC Router - Service Manual',
        [
            ('1. Safety', [
                'Always engage the emergency stop and wait for the spindle to coast to a stop (about 15 seconds) before opening the dust shoe.',
                'Wear hearing protection: the spindle reaches 86 dB at 18,000 rpm.',
            ]),
            ('2. Specifications', [
                'Working area 1220 x 1220 mm (48 x 48 in); Z travel 150 mm.',
                'Spindle: 2.2 kW water-cooled, 6,000-24,000 rpm, ER20 collet.',
                'Rapid traverse 15 m/min; positioning repeatability 0.03 mm.',
            ]),
            ('3. Maintenance schedule', [
                'Every 8 hours: vacuum the gantry rails and wipe the linear guides with a lint-free cloth.',
                'Every 40 hours: grease the linear bearings with NLGI 2 lithium grease, 2 pumps per bearing block.',
                'Every 500 hours: replace the spindle coolant (50/50 distilled water and propylene glycol, 6 litres) and check the ball screw backlash; above 0.05 mm, replace the ball nut.',
            ]),
            ('4. Alarm codes', [
                'ALM-3 - Spindle coolant flow low: the pump delivers less than 2 litres per minute. Check the reservoir level and the inlet strainer.',
                'ALM-9 - Limit switch hit on X: jog the axis back off the switch in the opposite direction, then re-home.',
                'ALM-14 - Spindle overheat above 45 C: stop the job, let the spindle cool for 20 minutes and check coolant flow.',
            ]),
        ],
    ),
    'bw90-dishwasher': (
        'Brightwave BW-90 Commercial Dishwasher - Installation and Care Guide',
        [
            ('1. Installation', [
                'Water supply: 2 to 4 bar inlet pressure; inlet water hardness should be below 7 dH, otherwise fit the BW-SOFT softener.',
                'Electrical: 400 V three-phase, 32 A breaker. The booster heater draws 9 kW.',
            ]),
            ('2. Cycle data', [
                'Wash tank temperature 60 C; final rinse temperature 82 C (sanitising).',
                'Cycle times: 60 s light, 90 s normal, 120 s heavy. Capacity up to 40 racks per hour on the light cycle.',
            ]),
            ('3. Cleaning and maintenance', [
                'After every service: drain the tank, remove and rinse the filter baskets, and leave the door open to dry.',
                'Weekly: descale with BW-DESCALE at 1 litre per 50 litres of tank water if limescale is visible on the wash arms.',
                'Every 3 months: check the rinse-aid and detergent dosing hoses for cracks.',
            ]),
            ('4. Error codes', [
                'F2 - Tank does not fill within 4 minutes: check the inlet tap is open and the inlet filter screen is clean.',
                'F5 - Final rinse below 82 C: the booster heater is not reaching temperature; check the 9 kW element and its contactor.',
                'F8 - Drain pump blocked: switch off, drain the tank manually and remove debris from the pump impeller.',
            ]),
        ],
    ),
    'af60-air-compressor': (
        'AeroFlow AF-60 Rotary Screw Compressor - Owner Manual',
        [
            ('1. Safety', [
                'Isolate power and vent the receiver to 0 bar before removing any panel. Stored pressure can reach 10 bar.',
                'The compressor restarts automatically on demand; lock out the main isolator before service.',
            ]),
            ('2. Specifications', [
                'Free air delivery 6.0 m3/min at 8 bar; maximum working pressure 10 bar.',
                'Motor 37 kW; noise level 68 dB(A) at 1 m.',
                'Oil capacity 18 litres of AF-SYN 46 synthetic compressor oil.',
            ]),
            ('3. Service intervals', [
                'Daily: drain the receiver condensate (automatic drain fitted; check it cycles every 10 minutes).',
                'Every 2000 hours: replace the air filter (AF-AIR-60) and the oil filter (AF-OIL-60).',
                'Every 4000 hours: replace the oil separator (AF-SEP-60) and the oil; check the drive belt tension.',
            ]),
            ('4. Fault messages', [
                'HIGH DISCHARGE TEMP (above 105 C): clean the cooler fins, check the oil level and the room ventilation; ambient must stay below 40 C.',
                'MOTOR OVERLOAD: check the supply voltage on all three phases and the motor current against 68 A full load.',
                'SEPARATOR DP HIGH (pressure drop above 1 bar across the oil separator): replace the separator element AF-SEP-60.',
            ]),
        ],
    ),
}

MARKDOWN = """# FrostLine RC-14 Reach-In Freezer - Quick Reference

## Temperatures
- Set point -18 C; the high-temperature alarm sounds at -12 C after 30 minutes.
- Defrost runs every 6 hours for up to 25 minutes and ends at an evaporator temperature of 10 C.

## Cleaning
- Clean the condenser coil every 30 days with a soft brush; a blocked coil raises energy use by up to 30%.
- Door gaskets: wipe weekly with warm soapy water; replace when torn (part RC-GASKET-14).

## Alarm codes
- A1 - Cabinet too warm: check the door is closed and the condenser coil is clean.
- A3 - Evaporator probe failure: the controller switches to timed defrost; replace probe RC-PROBE-E.
- A6 - Door open longer than 3 minutes: close the door; the fans stop while it is open.
"""


def write_pdf(path: Path, title: str, sections: list[tuple[str, list[str]]]) -> None:
    doc = pymupdf.open()
    doc.set_metadata({'title': title, 'author': 'demo manuals'})
    for heading, paras in sections:  # one section per page, like a real manual's chapters
        page = doc.new_page(width=595, height=842)  # A4
        y = 60
        page.insert_text((50, y), title, fontsize=9, color=(0.4, 0.4, 0.4))
        y += 30
        page.insert_text((50, y), heading, fontsize=16)
        y += 28
        for p in paras:
            rect = pymupdf.Rect(50, y, 545, y + 120)
            page.insert_textbox(rect, p, fontsize=11)
            y += 18 * (len(p) // 85 + 2)
    doc.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, (title, sections) in MANUALS.items():
        write_pdf(OUT / f'{slug}.pdf', title, sections)
    (OUT / 'rc14-freezer.md').write_text(MARKDOWN)
    print(sorted(p.name for p in OUT.iterdir()))


if __name__ == '__main__':
    main()
