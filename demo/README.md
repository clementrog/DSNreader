# DSN demo files

## ben-consulting-services-2026-04-demo-light-errors.dsn

Fichier de demo base sur la DSN source `DSN_DSN-mensuelle_Ben-Consulting-Services_7_employees_2026-04.dsn`, renomme et legerement modifie.

Anomalies attendues :

- PAS : le versement DGFIP declare `2851.00` alors que la somme salariee vaut `2841.21`. Ecart attendu : `9.79`.
- URSSAF : le CTP `959D` reste present dans la liste complete des CTP, mais sa base declarative a ete modifiee. Montant reconstruit attendu : `178.08`, montant salarie attendu : `172.07`, ecart attendu : `6.01`.

Points propres conserves pour la demo :

- declaration mensuelle avril 2026, periode declaree du `01/04/2026` au `24/04/2026` ;
- 7 salaries ;
- sortie salarie propre pour `RABY Augustin`, avec date de fin et motif de rupture `034` ;
- liste URSSAF complete conservee : `027`, `100D`, `100P`, `260`, `332`, `423`, `430`, `635`, `726D`, `726P`, `772`, `937`, `959`, `992`, `668`, `669` ;
- les autres rapprochements restent OK ou sous les tolerances d'arrondi existantes.
