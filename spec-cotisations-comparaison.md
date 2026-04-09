# Spec d'implémentation - modèle de comparaison des cotisations DSN

## 1. Objectif

Construire une nouvelle couche de lecture et de rapprochement au-dessus du parseur DSN actuel pour comparer, dans un même fichier DSN :

- les montants agrégés déclarés à un organisme ;
- les montants reconstitués à partir des blocs détaillés ;
- les montants individuels portés par salarié ;
- l'écart entre ces trois vues.

Le périmètre de cette première version couvre 5 familles :

- URSSAF
- PAS (prélèvement à la source)
- prévoyance
- mutuelle
- retraite complémentaire

## 2. Ce qu'on construit, en langage simple

Le parseur actuel sait déjà découper un fichier DSN en grands morceaux.

Ce qui manque aujourd'hui est une couche qui répond à la question métier :

"Le total payé à un organisme est-il cohérent avec le détail des cotisations et avec la somme des salariés ?"

Cette couche n'a pas vocation à recalculer toute la paie. Elle doit :

- lire les blocs DSN déjà présents dans le fichier ;
- les regrouper proprement ;
- faire des additions et des rapprochements ;
- produire un résultat explicable.

## 3. Constat sur le dépôt actuel

Le dépôt contient déjà la bonne base technique :

- le parseur découpe le fichier par niveau fichier / établissement / salarié / `S21.G00.54`
- l'extracteur actuel sait déjà agréger quelques montants simples
- les docs Publicodes nécessaires sont embarquées dans `docs/13. DSN`

En revanche, il n'existe pas encore de couche dédiée pour :

- reconstruire les blocs répétés `S21.G00.20`, `S21.G00.23`, `S21.G00.55`, `S21.G00.78`, `S21.G00.81`
- relier les blocs organisme / contrat / affiliation / adhésion
- sortir des écarts de rapprochement

## 4. Sources normatives à utiliser

La logique métier doit être dérivée des fichiers suivants :

- `docs/13. DSN/13.3-dsn-donnees-paie-rh.publicodes`
- `docs/13. DSN/13.1-cotisations-dsn.publicodes`

Repères confirmés :

- URSSAF versement : `S21.G00.20.005` autour des lignes 240-263 de `13.3`
- URSSAF bordereau : `S21.G00.22.005` autour des lignes 902-923 de `13.3`
- URSSAF cotisations agrégées par CTP : `S21.G00.23` lignes 924-1734 de `13.3`
- retraite complémentaire agrégée : `S21.G00.20.005` autour des lignes 368-635 de `13.3`
- PAS / DGFIP : `S21.G00.20.001 = DGFIP` autour des lignes 860-900 de `13.3`
- PAS individuel : `S21.G00.50.009` ligne 2696 de `13.3`
- composants de versement prévoyance / mutuelle : `S21.G00.55` lignes 3718-4044 de `13.3`
- bases assujetties et cotisations individuelles : `S21.G00.78` et `S21.G00.81` lignes 1-1525 de `13.1`
- affiliations et adhésions : `S21.G00.15` et `S21.G00.70` dans `13.3`

Référence externe : [cahier technique DSN 2026.1](https://www.net-entreprises.fr/media/documentation/dsn-cahier-technique-2026.1.pdf)

Important :

- les fichiers Publicodes servent ici de source normative pour comprendre les correspondances et les clés ;
- ils ne doivent pas être exécutés dans cette version ;
- la comparaison porte sur le contenu réel du fichier DSN parsé.

## 5. Glossaire simple

- Bloc : un petit groupe de lignes DSN qui décrivent un même objet. Exemple : un versement organisme.
- Montant agrégé : le total déclaré à un organisme au niveau établissement.
- Montant individuel : la somme portée au niveau salarié.
- Rapprochement : la vérification que deux totaux censés représenter la même chose sont égaux.
- Clé de rapprochement : les champs utilisés pour relier deux informations qui parlent du même contrat ou du même organisme.
- Organisme : l'entité qui reçoit la cotisation ou le versement.
- Affiliation : le rattachement technique d'un salarié à un contrat.
- Adhésion : l'identifiant technique du contrat côté organisme.

## 6. Périmètre fonctionnel

La version 1 doit produire :

- des comparaisons par établissement ;
- une synthèse globale tous établissements confondus ;
- le détail des écarts par famille de cotisation ;
- les clés de regroupement utilisées ;
- les lignes DSN impliquées dans chaque calcul ;
- un statut lisible : `ok`, `ecart`, `manquant`, `non_rattache`, `non_calculable`

La version 1 ne doit pas :

- recalculer les règles de paie Publicodes ;
- interpréter les montants hors fichier DSN ;
- corriger automatiquement les écarts ;
- inférer un rattachement ambigu sans règle explicite.

## 7. Décision d'architecture recommandée

### 7.1 Recommandation CTO

Ne pas réécrire le parseur.

Il faut ajouter une couche dédiée, au-dessus du parseur actuel, pour reconstruire les blocs métiers nécessaires au rapprochement.

Pourquoi c'est important :

- c'est plus rapide à livrer ;
- on garde l'existant stable ;
- on limite le risque de casser les tests déjà en place ;
- on peut tester la nouvelle logique de façon isolée.

### 7.2 Modules à ajouter

Recommandation :

- `dsn_extractor/contributions.py` — logique métier de rapprochement
- `dsn_extractor/block_groups.py` — utilitaire de regroupement de blocs DSN
- `dsn_extractor/organisms.py` — référentiel DATA-ORGANISME (dict Python)

Évolution du schéma :

- `dsn_extractor/models.py`

Tests :

- `tests/test_contributions.py`
- nouveaux fixtures DSN dédiés dans `tests/fixtures/`

## 8. Jeu de données DATA-ORGANISME

Le tableau fourni par le métier doit devenir une donnée versionnée dans le dépôt.

Format retenu pour la v1 :

- module Python `dsn_extractor/organisms.py`
- dict `ORGANISM_REGISTRY: dict[str, tuple[str, str]]` mappant `organism_id -> (organism_label, family_code)`
- cohérent avec le pattern existant de `dsn_extractor/enums.py`

Pourquoi un module Python plutôt qu'un TSV :

- pas de parsing ni d'I/O fichier à gérer ;
- pas de gestion d'erreurs de format ;
- pattern identique à celui des enums existants ;
- ~400 entrées : parfaitement adaptée à un dict Python.

Règles :

- `organism_id` est la clé technique principale ;
- si un code organisme DSN n'existe pas dans ce référentiel, le rapprochement reste possible mais le résultat doit porter un warning `organism_unknown_in_reference`.

Usage attendu du référentiel :

- enrichir les libellés ;
- distinguer les grands univers d'organismes ;
- valider les correspondances attendues ;
- ne pas servir de source principale pour distinguer prévoyance et mutuelle.

Décision importante :

- la distinction "prévoyance" vs "mutuelle" doit être reconstruite à partir des clés DSN de liaison ;
- `DATA-ORGANISME` sert à enrichir, à valider et à afficher ;
- `DATA-ORGANISME` ne doit pas être utilisé pour deviner une famille métier quand les clés DSN existent.

## 9. Reconstruction des blocs DSN nécessaires

### 9.1 Principe général

Le parseur actuel stocke les enregistrements de manière plate à l'intérieur d'un établissement ou d'un salarié.

La nouvelle couche doit reconstruire des blocs logiques et leurs relations parent-enfant.

### 9.2 Blocs établissement à reconstruire

À partir de `est.records`, reconstruire :

- `S21.G00.15` : adhésion prévoyance / mutuelle
- `S21.G00.20` : versement organisme
- `S21.G00.22` : bordereau de cotisation due
- `S21.G00.23` : cotisation agrégée (enfant de `S21.G00.22`)
- `S21.G00.55` : composant du versement (enfant de `S21.G00.20`)

Règle de découpage (blocs plats) :

- un nouveau bloc commence quand le suffixe `.001` du préfixe concerné apparaît ;
- toutes les lignes du même préfixe suivant ce départ appartiennent à ce bloc jusqu'au prochain `.001` du même préfixe ou jusqu'à la fin de l'établissement.

### 9.3 Relations parent-enfant établissement

La hiérarchie DSN au niveau établissement est :

```
S21.G00.20 (versement OPS)     → ce qu'on PAIE
  └── S21.G00.55 (composant du versement)
S21.G00.22 (bordereau)          → ce qu'on DOIT
  └── S21.G00.23 (cotisation agrégée par CTP)
```

Algorithme de rattachement :

Itérer séquentiellement sur `est.records`. Maintenir un pointeur `current_s20` et un pointeur `current_s22`.

- quand `S21.G00.20.001` apparaît : ouvrir un nouveau bloc `S20`, le devenir `current_s20` ; réinitialiser `current_s22` ;
- quand `S21.G00.55.001` apparaît : ouvrir un nouveau bloc `S55`, le rattacher à `current_s20` ; si `current_s20` est `None`, émettre un warning `orphan_s55_block` ;
- quand `S21.G00.22.001` apparaît : ouvrir un nouveau bloc `S22`, le devenir `current_s22` ;
- quand `S21.G00.23.001` apparaît : ouvrir un nouveau bloc `S23`, le rattacher à `current_s22` ; si `current_s22` est `None`, émettre un warning `orphan_s23_block` ;
- les autres lignes du même préfixe complètent le bloc courant.

Ce mécanisme est le même que celui du parseur actuel pour `S21.G00.54` : la position séquentielle détermine l'appartenance.

### 9.4 Blocs salarié à reconstruire

À partir de `emp.records`, reconstruire :

- `S21.G00.50` : rémunération (pour PAS individuel) — **tous les blocs, pas seulement le premier**
- `S21.G00.70` : affiliation prévoyance / mutuelle
- `S21.G00.78` : base assujettie
- `S21.G00.81` : cotisation individuelle (enfant de `S21.G00.78`)

Règle de découpage :

- un nouveau `S21.G00.50` commence à `S21.G00.50.001` ;
- un nouveau `S21.G00.70` commence quand un enregistrement `S21.G00.70.*` apparaît après un enregistrement d'un autre préfixe, ou à la première occurrence ;
- un nouveau `S21.G00.78` commence à `S21.G00.78.001` ;
- un nouveau `S21.G00.81` commence à `S21.G00.81.001` ;
- les blocs `S21.G00.81` sont rattachés au dernier `S21.G00.78` ouvert (même algorithme "current parent" que pour les blocs établissement).

Point important sur `S21.G00.79` :

- les enregistrements `S21.G00.79` (composant de base assujettie, tranches A/B/C) apparaissent entre `S21.G00.78` et `S21.G00.81` dans le fichier ;
- ils ne sont pas utilisés pour le rapprochement en v1 ;
- ils ne doivent jamais interrompre le groupement `78 → 81` ;
- le groupeur doit les ignorer sans casser la relation parent-enfant.

Raison :

- le rapprochement prévoyance / mutuelle / retraite dépend du lien entre `78` et les `81` attachés à cette base.

## 10. Clés de rapprochement par famille

Le système doit éviter de comparer des montants qui ne parlent pas du même objet.

Chaque famille utilise une clé minimale adaptée à sa complexité :

### PAS

Clé : `(establishment_siret)`

Un seul organisme DGFIP par établissement. Le rapprochement est global.

### URSSAF

Clé : `(establishment_siret, organism_id)`

Un organisme URSSAF par établissement (dans le cas standard). Le détail CTP est un sous-niveau, pas une clé de regroupement.

### Retraite

Clé : `(establishment_siret, organism_id)`

Un ou plusieurs organismes AAR par établissement. Le rapprochement se fait par caisse quand le lien est explicite.

### Prévoyance / Mutuelle

Clé : `(establishment_siret, organism_id, adhesion_id, affiliation_id, contract_ref)`

Seules ces familles nécessitent une clé enrichie pour relier les 3 niveaux (versement, composant, individuel).

### Règles communes

- si la clé n'est pas suffisante pour faire un lien fiable, le statut doit être `non_rattache` ;
- une comparaison ne doit utiliser que les champs disponibles et non ambigus.

## 11. Tables de correspondance internes à reconstruire

Pour prévoyance et mutuelle, 2 tables de jointure internes enrichissent le rapprochement.

**Important** : dans le périmètre visé par cet outil, ces blocs sont considérés comme structurants pour le rattachement. Ils ne sont pas "optionnels métier".

### 11.1 Registre des adhésions établissement

Source : `S21.G00.15`

Champs utiles :

- `contract_ref` = `S21.G00.15.001`
- `organism_id` = `S21.G00.15.002`
- `adhesion_id` = `S21.G00.15.005`
- `family` déduite par le tiroir DSN reconstitué et le chaînage métier

But :

- relier un contrat ou une référence de composant à un organisme et à une adhésion.

### 11.2 Registre des affiliations salarié

Source : `S21.G00.70`

Champs utiles :

- `affiliation_id` = `S21.G00.70.012`
- `adhesion_id` = `S21.G00.70.013`
- `family` héritée du rattachement contrat / adhésion / affiliation reconstitué

But :

- relier une affiliation individuelle à l'adhésion technique du contrat.

### 11.3 Comportement en cas de DSN incohérente

Quand `S21.G00.15` ou `S21.G00.70` manquent alors qu'ils sont nécessaires au rattachement :

- ne pas inventer de rapprochement simplifié par `organism_id` seul ;
- émettre un warning `missing_structuring_block_s15` ou `missing_structuring_block_s70` ;
- conserver les montants bruts calculables ;
- positionner le rapprochement en `non_rattache`.

## 12. Modèle de sortie recommandé

Le modèle de sortie doit être ajouté à `DSNOutput` sans casser les champs existants.

Structure recommandée :

```python
class ContributionComparisonDetail(BaseModel):
    """Ligne de détail dans un rapprochement (CTP, salarié, contrat...)."""
    key: str
    label: str | None = None
    declared_amount: Decimal | None = None
    computed_amount: Decimal | None = None
    delta: Decimal | None = None
    status: str = "ok"
    record_lines: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ContributionComparisonItem(BaseModel):
    """Un rapprochement pour un organisme dans une famille."""
    family: str                             # urssaf | pas | prevoyance | mutuelle | retraite
    organism_id: str | None = None
    organism_label: str | None = None

    # Montants des différentes sources
    aggregate_amount: Decimal | None = None    # S21.G00.20.005
    bordereau_amount: Decimal | None = None    # S21.G00.22.005 (URSSAF uniquement)
    component_amount: Decimal | None = None    # somme S21.G00.23 ou S21.G00.55
    individual_amount: Decimal | None = None   # somme individus (S50/S81)

    # Écarts calculés — seuls les écarts pertinents pour la famille sont renseignés
    aggregate_vs_bordereau_delta: Decimal | None = None   # URSSAF : 20 vs 22
    bordereau_vs_component_delta: Decimal | None = None   # URSSAF : 22 vs sum(23)
    aggregate_vs_component_delta: Decimal | None = None    # prévoyance/mutuelle : 20 vs sum(55)
    aggregate_vs_individual_delta: Decimal | None = None   # toutes familles : 20 vs sum(individus)

    status: str = "ok"
    details: list[ContributionComparisonDetail] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Clés de rapprochement enrichies (prévoyance/mutuelle uniquement)
    adhesion_id: str | None = None
    contract_ref: str | None = None


class ContributionComparisons(BaseModel):
    """Collection de tous les rapprochements d'un établissement."""
    items: list[ContributionComparisonItem] = Field(default_factory=list)
    ok_count: int = 0
    mismatch_count: int = 0
    warning_count: int = 0
```

Intégration recommandée :

- un champ `contribution_comparisons` au niveau établissement ;
- un champ `global_contribution_comparisons` au niveau `DSNOutput`.

Règle de sérialisation JSON :

- les champs delta à `None` sont omis du JSON (`exclude_none=True`) pour éviter le bruit ;
- chaque famille ne produit que les deltas qui la concernent.

Pourquoi ce modèle est recommandé :

- il est lisible côté produit ;
- il garde les montants bruts ;
- il garde les écarts ;
- il permet de tracer quelles lignes DSN ont servi ;
- il distingue clairement les 3 étages URSSAF (versement / bordereau / CTP).

## 13. Règles métier par famille

### 13.1 URSSAF

### Architecture des blocs URSSAF

La norme DSN distingue 3 blocs au niveau établissement :

```
S21.G00.20 (versement OPS)     → montant effectivement payé
S21.G00.22 (bordereau)         → montant total des cotisations dues
  └── S21.G00.23 (cotisation agrégée)  → détail par code CTP
```

Le bon chaînage est `20 ↔ 22 ↔ 23`, jamais `20 ↔ 23` directement.

Référence locale : `13.3-dsn-donnees-paie-rh.publicodes` lignes 902-923.

### Source versement

- `S21.G00.20.005` = montant du versement
- Filtre : `S21.G00.20.001` correspond à un organisme URSSAF (type `URS` dans `DATA-ORGANISME`)

### Source bordereau

- `S21.G00.22.005` = montant total de cotisations
- `S21.G00.22.001` = identifiant organisme (même URSSAF que le versement)
- `S21.G00.22.006` = identifiant CRM de régularisation (si non vide : taguer le contrôle comme contenant une régularisation)

### Source détaillée (CTP)

- `S21.G00.23` rattaché au `S21.G00.22` parent (algorithme séquentiel de section 9.3)

Clé de détail :

- `(ctp_code, assiette_qualifier, insee_code)`

Champs utiles :

- `ctp_code` = `S21.G00.23.001`
- `assiette_qualifier` = `S21.G00.23.002`
- `rate` = `S21.G00.23.003` (en pourcentage, ex: `7.30` pour 7,30%)
- `base` = `S21.G00.23.004`
- `declared_amount` = `S21.G00.23.005`
- `insee_code` = `S21.G00.23.006`

### Calcul

Décision verrouillée :

- si `S21.G00.23.005` est renseigné, il est traité comme montant déclaré ;
- si `S21.G00.23.003` (taux) est aussi renseigné, un contrôle secondaire compare `declared_amount` vs `recomputed_amount` ;
- `recomputed_amount = round(base * rate / 100, 2)` ;
- si `23.005` est vide mais `base` et `rate` sont présents, utiliser `recomputed_amount` ;
- si aucun montant n'est calculable, le détail est `non_calculable`.

### Contrôles à produire

- **contrôle 1** : `S21.G00.20.005` (versement) == `S21.G00.22.005` (bordereau)
- **contrôle 2** : `S21.G00.22.005` (bordereau) == somme des montants détaillés retenus des `S21.G00.23`
- **contrôle 3** (secondaire) : pour chaque ligne CTP calculable, `declared_amount` ≈ `recomputed_amount`

### Tolérance URSSAF

La tolérance pour les contrôles 2 et 3 est dynamique :

```
tolerance = max(0.01, 0.01 * nombre_de_lignes_CTP_recalculées)
```

Justification : chaque CTP est arrondi indépendamment à 2 décimales, ce qui génère une erreur d'arrondi cumulée pouvant atteindre `0.005 × N_lignes`. Avec ~29 CTP courants, la tolérance fixe de `0.01` produirait des faux écarts systématiques.

Le contrôle 1 (versement vs bordereau) garde une tolérance fixe de `0.01` car c'est une comparaison de deux montants déjà arrondis.

### Référence normative

- `13.3`, lignes 240-263 pour `S21.G00.20`
- `13.3`, lignes 902-923 pour `S21.G00.22`
- `13.3`, lignes 924-1734 pour `S21.G00.23`

### Décision produit

La sortie URSSAF doit exposer 3 niveaux :

- versement organisme (`S21.G00.20.005`)
- bordereau cotisation due (`S21.G00.22.005`)
- détail par CTP (`S21.G00.23`)

### 13.1.1 Rattachement code CTP → cotisation individuelle (S21.G00.81.001)

#### Objectif

Permettre une vue "par salarié" uniquement quand la norme DSN rend le lien explicite entre un code CTP d'établissement (`S21.G00.23.001`) et un code de cotisation individuelle (`S21.G00.81.001`). Pas d'invention de mapping.

#### Règle produit

- Un code CTP est "rattachable" si et seulement si la norme `13.1-cotisations-dsn.publicodes` associe explicitement ce code à UN code individuel `S21.G00.81.001`, avec un OPS égal à `entreprise . urssaf . SIRET`.
- Par défaut un code CTP est NON rattachable (default-deny).
- Les codes non rattachables gardent leur ligne au niveau bordereau / code ; l'UI affichera `non_rattache` au lieu d'une ventilation par salarié.
- La table de mapping verrouillée est la seule source de vérité pour le moteur (voir Slice C de la roadmap). Toute entrée ajoutée doit référencer la ligne publicodes exacte et le code individuel `S81.001` correspondant.

#### Statuts de détail URSSAF (ajout)

- `non_rattache` : code comptable au niveau code mais pas de chemin DSN fiable vers une allocation individuelle. Affichage prévu en Slice D.
- `non_calculable` : (inchangé) données manquantes pour calculer la comparaison.

La liste canonique des statuts autorisés est exposée par le module `dsn_extractor.urssaf_individual_mapping` via la constante `URSSAF_DETAIL_STATUSES`.

#### Source de vérité code

- Table : `dsn_extractor/data/urssaf_individual_mapping.tsv`
- Chargeur + API : `dsn_extractor/urssaf_individual_mapping.py`
  - `load_mapping() -> dict[str, UrssafIndividualMapping]`
  - `is_urssaf_code_mappable(ctp_code) -> bool`
  - `get_individual_code_for_ctp(ctp_code) -> str | None`
- Tests : `tests/test_urssaf_mapping.py`

Le module est volontairement découplé de `_compute_urssaf`. Slice B est un "gate" documentaire + scaffolding : la logique de reconcilation individuelle (branchement dans `_compute_urssaf`) est livrée en Slice C.

#### Table de mapping verrouillée (avril 2026)

| CTP | Libellé | Code S81.001 | OPS | Source normative | Statut |
|-----|---------|--------------|-----|------------------|--------|
| 027 | CONTRIBUTION AU DIALOGUE SOCIAL | 100 | urssaf_siret | publicodes 13.1 L235-247 | rattachable |

#### Journal des décisions

- **2026-04-09** — Ouverture de la gate. CTP `027` verrouillé comme premier cas rattachable sur la base de "DIALOGUE SOCIAL 100" dans `docs/13. DSN/13.1-cotisations-dsn.publicodes` lignes 235-247 (code individuel `100`, OPS `entreprise . urssaf . SIRET`, montant `salarié . cotisations . contribution au dialogue social`). Correspondance locale confirmée par `dsn_extractor/data/ctp_rate_reference.tsv:28` (CTP `027`, libellé "CONTRIBUTION AU DIALOGUE SOCIAL", taux 0.016%, effective 01/01/2015). La référence à `8270` dans `roadmap.md` était une erreur et a été corrigée vers `027` dans le même commit.

### 13.2 PAS

### Source agrégée

Source :

- `S21.G00.20.005`

Filtre :

- `S21.G00.20.001 == 'DGFIP'`

Décision verrouillée :

- un seul bloc DGFIP est attendu par établissement ;
- si plusieurs blocs `S21.G00.20` avec `001 == 'DGFIP'` sont trouvés, émettre un warning `multiple_dgfip_blocks` et sommer les montants.

### Source individuelle

Source :

- somme de **toutes les occurrences** de `S21.G00.50.009` de tous les salariés

Point important :

- un salarié peut avoir plusieurs blocs `S21.G00.50` (rappel de salaire, régularisation, etc.) ;
- il faut sommer toutes les occurrences de `S21.G00.50.009` par salarié, pas seulement la première ;
- cela implique d'utiliser `_find_all_values()` au lieu de `_find_value()` pour ce champ.

### Calcul

- `aggregate_amount = S21.G00.20.005 where 20.001 == 'DGFIP'`
- `individual_amount = sum(tous les S21.G00.50.009 de tous les salariés)`

### Contrôle à produire

- `aggregate_amount == individual_amount` (tolérance : `0.01`)

### Référence normative

- `13.3`, lignes 860-900 pour le versement DGFIP
- `13.3`, ligne 2696 pour le PAS individuel

### Détail à conserver

La sortie doit inclure la liste des salariés ayant un PAS non nul :

- nom affiché salarié
- montant individuel PAS (somme de tous les blocs `S50` du salarié)
- lignes DSN utilisées

### 13.3 Prévoyance

### Vue métier à rapprocher

Trois niveaux doivent être rapprochés :

- niveau versement organisme : `S21.G00.20.005`
- niveau composant de versement : `S21.G00.55.001`
- niveau individuel : somme des `S21.G00.81.004` rattachés aux `S21.G00.78` de code `31`

### Sources

Niveau versement organisme :

- `S21.G00.20.001` = code organisme
- `S21.G00.20.005` = montant du versement

Niveau composant :

- `S21.G00.55.001` = montant versé
- `S21.G00.55.003` = référence contrat
- `S21.G00.55.004` = période

Niveau individuel :

- `S21.G00.78.001 == 31`
- `S21.G00.78.005` = identifiant technique affiliation
- `S21.G00.78.006` = numéro de contrat
- `sum(S21.G00.81.004)` = montant individuel

Tables de pont structurantes :

- `S21.G00.15` pour relier `contract_ref -> organism_id + adhesion_id`
- `S21.G00.70` pour relier `affiliation_id -> adhesion_id`

### Clé de rapprochement

Clé prévoyance :

- le niveau `20` s'exprime par `organism_id`
- le niveau `55` s'exprime par `contract_ref`, relié via `S21.G00.15`
- le niveau `78/81` s'exprime par `affiliation_id + contract_ref`, relié via `S21.G00.15` et `S21.G00.70`
- si ces liens structurants sont absents, le fichier est traité comme incohérent pour ce rapprochement

### Contrôles à produire

- somme des composants `55` rattachés à un organisme = montant `20`
- somme des montants individuels `81.004` rattachés à cet organisme = montant `20`
- somme des montants individuels `81.004` rattachés au contrat = montant `55.001`

### Référence normative

- `13.3`, lignes 691-713 pour `S21.G00.20`
- `13.3`, lignes 3718-3874 pour `S21.G00.55`
- `13.1`, lignes 554-947 pour `S21.G00.78/81` prévoyance
- `13.3`, lignes 127-153 pour `S21.G00.15`
- `13.3`, lignes 4542-4679 pour `S21.G00.70`

### 13.4 Mutuelle

La logique est la même que prévoyance, mais la famille métier est distincte.

Pourquoi séparer les deux :

- produit, reporting et lecture métier sont plus clairs ;
- les contrats et options mutuelle peuvent être nombreux ;
- on évite les faux rapprochements entre prévoyance et mutuelle.

### Sources

Niveau versement organisme :

- `S21.G00.20.001`
- `S21.G00.20.005`

Niveau composant :

- `S21.G00.55.001`
- `S21.G00.55.003`
- `S21.G00.55.004`

Niveau individuel :

- `S21.G00.78.001 == 31`
- `S21.G00.78.005`
- `S21.G00.78.006`
- `sum(S21.G00.81.004)`

Tables de pont structurantes :

- `S21.G00.15` mutuelle
- `S21.G00.70` mutuelle

### Contrôles à produire

- somme des composants `55` d'une mutuelle = montant `20`
- somme des montants individuels rattachés à cette mutuelle = montant `20`
- somme des montants individuels rattachés à un contrat mutuelle = montant `55.001`

### Référence normative

- `13.3`, lignes 752-774 pour `S21.G00.20`
- `13.3`, lignes 3875-4044 pour `S21.G00.55`
- `13.1`, lignes 948-1380 pour `S21.G00.78/81` mutuelle
- `13.3`, lignes 154-181 pour `S21.G00.15`
- `13.3`, lignes 4685-5139 pour `S21.G00.70`

### 13.5 Retraite complémentaire

### Vue métier à rapprocher

Comparer :

- le montant total de versement organisme `S21.G00.20.005`
- la somme des montants individuels rattachés aux bases `02` et `03`

### Source agrégée

Source :

- `S21.G00.20.001` = SIRET caisse de retraite
- `S21.G00.20.005` = montant total du versement

Filtre :

- organisme présent dans `DATA-ORGANISME`
- famille métier `retraite`

### Source individuelle

Filtre base :

- `S21.G00.78.001 in {"02", "03"}`

Filtre cotisation individuelle :

- `S21.G00.81.001 in {"131", "132", "106", "109"}`

Montant :

- somme des `S21.G00.81.004` rattachés aux bases retenues

Point important sur les montants négatifs :

- le code `106` (réduction générale cotisations patronales retraite) produit un montant **négatif** (`0 - exonération`) ;
- le code `109` (exonération retraite apprentis) produit un montant **négatif** ;
- ces montants négatifs restent dans la somme car le versement agrégé (`S21.G00.20.005`) est net d'exonérations ;
- le total individuel est donc un montant net (brut cotisations - exonérations), cohérent avec le versement.

### Contrôle à produire

- `aggregate_amount == individual_amount` (tolérance : `0.01`)

### Référence normative

- `13.3`, lignes 368-635 pour le versement retraite complémentaire
- `13.1`, lignes 1-96 pour la base `03`
- `13.1`, lignes 402-545 pour la base `02`
- `13.1`, lignes 310-325 pour le code `106` (RGCP retraite, montant négatif)
- `13.1`, lignes 367-374 pour le code `109` (exonération apprentis, montant négatif)

### Limite volontaire de la version 1

Si plusieurs caisses de retraite sont présentes dans un même établissement et qu'aucune clé explicite ne permet de répartir les montants individuels par caisse, le système doit :

- agréger par caisse côté `S21.G00.20`
- calculer un total individuel établissement
- produire un warning `multiple_retirement_organisms_unallocated`
- ne pas inventer de ventilation.

## 14. Statuts de contrôle et tolérance

### Statuts autorisés

- `ok` — les montants comparés sont tous présents et dans la tolérance
- `ecart` — les montants comparés sont présents mais hors tolérance
- `manquant_agrege` — le bloc agrégé (`S21.G00.20`) n'existe pas
- `manquant_bordereau` — le bordereau (`S21.G00.22`) n'existe pas (URSSAF)
- `manquant_detail` — les blocs de détail (`S21.G00.23`, `S21.G00.55`) n'existent pas
- `manquant_individuel` — aucun montant individuel trouvé
- `non_rattache` — les blocs existent mais ne peuvent pas être reliés sans ambiguïté
- `non_calculable` — les champs nécessaires au calcul sont absents

### Tolérance par famille

| Famille | Contrôle | Tolérance |
|---------|----------|-----------|
| PAS | agrégé vs individuel | `0.01` |
| URSSAF | versement vs bordereau (20 vs 22) | `0.01` |
| URSSAF | bordereau vs somme CTP (22 vs 23) | `max(0.01, 0.01 × N_lignes_CTP)` |
| URSSAF | déclaré vs recalculé par CTP | `0.01` |
| Retraite | agrégé vs individuel | `0.01` |
| Prévoyance | agrégé vs composant / individuel | `0.01` |
| Mutuelle | agrégé vs composant / individuel | `0.01` |

### Gestion des régularisations

Quand un identifiant CRM de régularisation est détecté (`S21.G00.20.013`, `S21.G00.22.006`, `S21.G00.55.005`) :

- conserver et afficher les montants calculés ;
- conserver le statut principal du rapprochement (`ok`, `ecart`, etc.) ;
- ajouter un warning explicite indiquant qu'une régularisation sur un mois précédent n'est pas correctement prise en compte par l'outil en v1 ;
- message recommandé :
  `Des régularisations DSN ont été détectées. Les éléments régularisés sur des mois précédents ne sont pas pris en compte correctement par cet outil en V1.`

## 15. Étapes d'implémentation recommandées

### Phase 1 - outillage

- créer `dsn_extractor/organisms.py` avec le dict `ORGANISM_REGISTRY`
- créer `dsn_extractor/block_groups.py` avec l'algorithme séquentiel de regroupement (section 9)
- ajouter les helpers de lecture multi-valeurs (`_find_all_values()` existe déjà, vérifier son usage)

### Phase 2 - modèle

- ajouter les modèles Pydantic de comparaison (section 12)
- brancher `contribution_comparisons` dans `Establishment` et `DSNOutput`

### Phase 3 - PAS

- implémenter PAS en premier

Pourquoi :

- c'est le cas le plus simple ;
- il valide la structure de sortie ;
- il crée le socle de tests sur un rapprochement agrégé vs individuel ;
- il force à résoudre le problème des blocs `S21.G00.50` multiples par salarié.

### Phase 4 - URSSAF

- implémenter les blocs `20`, `22`, `23` avec le chaînage `20 ↔ 22 ↔ 23`
- implémenter l'algorithme parent-enfant `22 → 23`
- sortir la somme par CTP avec double contrôle (bordereau vs CTP, versement vs bordereau)
- implémenter la tolérance dynamique

### Phase 5 - prévoyance / mutuelle

- implémenter l'algorithme parent-enfant `20 → 55`
- implémenter les ponts `15` + `70` comme clés structurantes
- implémenter les blocs `78` → `81` (en ignorant `79`)
- sortir les rapprochements à 3 niveaux

### Phase 6 - retraite

- implémenter les filtres `78.001 ∈ {02, 03}` et `81.001 ∈ {131, 132, 106, 109}`
- documenter dans les détails que 106 et 109 sont des montants négatifs
- gérer le cas multi-caisses avec warning explicite

## 16. Tests indispensables

À ajouter :

- un fixture PAS avec égalité parfaite
- un fixture PAS avec écart
- un fixture URSSAF avec plusieurs CTP
- un fixture URSSAF avec taux vide mais montant déclaré présent
- un fixture prévoyance avec `15 + 55 + 70 + 78 + 81`
- un fixture mutuelle avec plusieurs options
- un fixture retraite avec bases `02` et `03`
- un fixture avec organisme absent de `DATA-ORGANISME`
- un fixture avec rattachement ambigu
- un fixture multi-établissements

Les tests doivent vérifier :

- les montants ;
- les clés de rapprochement ;
- les statuts ;
- les warnings ;
- les numéros de ligne source ;
- l'agrégation globale.

## 17. Critères d'acceptation

Le travail sera considéré correct si :

- aucun test existant du parseur de base n'est cassé ;
- la nouvelle sortie est stable et validée par Pydantic ;
- chaque famille produit un résultat lisible ;
- chaque écart est expliqué par une clé, un montant, et des lignes source ;
- aucun rapprochement n'est fait sur une correspondance ambiguë ;
- `DATA-ORGANISME` est versionné dans le dépôt.

## 18. Décisions verrouillées

Les décisions métier suivantes sont verrouillées et ne doivent pas être remises en question pendant l'implémentation.

### URSSAF - traitement de S21.G00.23.005

- si `S21.G00.23.005` est renseigné, il est traité comme montant déclaré ;
- si `S21.G00.23.003` (taux) est aussi renseigné, un contrôle secondaire compare déclaré vs recalculé ;
- si `23.005` est vide mais base et taux sont présents, le recalculé est utilisé ;
- si rien n'est calculable, le statut est `non_calculable`.

### URSSAF - chaînage des blocs

- le chaînage est `20 ↔ 22 ↔ 23`, avec double contrôle (versement vs bordereau, bordereau vs somme CTP) ;
- pas de raccourci `20 ↔ 23` direct.

### PAS - unicité DGFIP

- un seul bloc DGFIP est attendu par établissement ;
- si plusieurs sont trouvés : warning `multiple_dgfip_blocks`, somme des montants.

### PAS - blocs S50 multiples

- sommer toutes les occurrences de `S21.G00.50.009` par salarié.

### Prévoyance / mutuelle - clé de rapprochement

- clé technique interne : `(organism_id, adhesion_id, affiliation_id, contract_ref)` ;
- `S21.G00.15` et `S21.G00.70` sont considérés comme structurants pour ce rattachement ;
- s'ils manquent, le rapprochement reste affiché avec ses montants bruts calculables mais son verdict devient `non_rattache`.

### Retraite - montants négatifs

- les codes `106` et `109` sont inclus dans la somme individuelle ;
- leurs montants sont négatifs (exonérations) ;
- le total individuel est net, cohérent avec le versement agrégé.

### Retraite - multi-caisses

- rapprochement par caisse quand le lien est explicite ;
- sinon, total individuel établissement global, avec warning `multiple_retirement_organisms_unallocated` ;
- pas de ventilation artificielle.

### DATA-ORGANISME - format

- module Python `organisms.py`, pas TSV ;
- cohérent avec le pattern `enums.py`.

### Régularisations - comportement v1

- les montants calculés restent affichés ;
- le verdict de rapprochement reste affiché ;
- un warning explicite précise que les régularisations portant sur des mois précédents ne sont pas correctement prises en compte en v1.

## 19. Frontend (spec minimale v1)

L'objectif immédiat est le moteur backend. La spec frontend est volontairement minimale pour v1.

### Section à ajouter dans l'interface

Ajouter une section "Rapprochement cotisations" après le bloc "Tracking gestionnaire", suivant le même pattern de rendu.

### Affichage par famille

Pour chaque `ContributionComparisonItem` :

- un bandeau avec : famille, organisme, statut (badge coloré)
- les montants : agrégé, bordereau (si URSSAF), composant (si prév/mut), individuel
- les deltas non nuls
- un tableau de détail dépliant (lignes CTP pour URSSAF, salariés pour PAS, contrats pour prév/mut/retraite)

### Badges de statut

- `ok` → vert
- `ecart` → rouge
- `manquant_*` → jaune
- `non_rattache` / `non_calculable` → gris

### Warning régularisation

- si une régularisation est détectée, afficher un bloc de vigilance sous le bandeau principal ;
- ce warning ne remplace pas le statut ;
- il explique que les montants sont affichés mais que les corrections portant sur des mois antérieurs ne sont pas correctement interprétées en v1.

### Compteurs résumé

En haut de la section : 3 compteurs (OK / Écarts / Warnings), identiques au pattern de complexité existant.
