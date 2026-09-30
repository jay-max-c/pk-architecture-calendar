# PK Architecture Calendar

Calendar project for **Cracow University of Technology (Politechnika Krakowska), Faculty of Architecture**.

Target timetable:

- Architecture, second-cycle degree
- **Year 1 / Semester 1**
- **M.D. in English**
- Academic year **2026/27**

## Official source

The updater checks the Faculty of Architecture timetable page:

https://arch.pk.edu.pl/dziekanat/plan-zajec/

It automatically locates the current **Year 1 / Semester 1 – M.D. in English** timetable PDF, downloads it, extracts its text/tables, and records the source hash.

The GitHub Action runs every 6 hours.

## Safety

The first stage only extracts and monitors the official timetable. It does **not** generate or overwrite the Apple Calendar feed until the current PDF layout has been validated. This prevents a PDF-layout change from creating incorrect class times.

## Professor / email changes

Use `overrides.json` for manual changes announced by professors. Manual overrides will take priority over the official timetable when calendar generation is enabled.

## Apple Calendar

The final feed will use:

- Europe/Warsaw timezone
- 30-minute reminder
- 5-minute reminder
- room / campus location
- manual professor overrides
