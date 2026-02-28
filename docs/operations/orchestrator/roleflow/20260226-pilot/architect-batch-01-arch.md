# Architect Pilot - BATCH-01-ARCH

- Decision: traiter le warning de drift comme faux positif pour streams en PASS.
- Change shape: validation doit signaler uniquement READY utiles (streams non PASS ou inconnus).
- Impact: reduction du bruit de monitoring, meilleur focus sur vrais blocages.
