# Fe F0 two-run preparation example

Edit every `/EDIT/absolute/path` in `campaign.json` on Perlmutter: use an empty new run root, shared nonempty POSCAR/INCAR/KPOINTS/POTCAR (cold: ISTART=0, ICHARG=2), working job template and an independently verified compatible q0 reference. The Fe settings are diagnostic candidates, not accepted defaults; reference compatibility is deferred to T3.

```sh
python -B -m dmi_pipeline campaign-prepare --campaign examples/fe-f0-pilot/campaign.json
python -B -m dmi_pipeline campaign-plan --root /EDIT/absolute/path/to/new-fe-f0-run-root
```

Neither command submits jobs or contacts a cluster. The minus case uses the same positive unwrapped q as the plus case; preparation reflects it once.
