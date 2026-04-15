# Notes de version - correction apprentis URSSAF `100 / 726`

Public visé : opérateurs paie, support, équipe produit.

## Ce qui change

- Les apprentis ne sont plus basculés en bloc dans `726`.
- La part sous seuil reste dans `726`.
- La part au-dessus du seuil repart dans `100`.
- Les lignes `100D`, `726D` et `863D` peuvent maintenant afficher un montant reconstitué quand la DSN ne porte pas directement le montant en `.005`.

## Effet attendu côté lecture métier

Sur les cas proches du dossier Thomas :

- `100P` ne doit plus manquer la part apprenti excédentaire.
- `726P` ne doit plus porter cette même part en trop.
- Les deux lignes doivent converger vers un rapprochement cohérent, voire `OK` quand la DSN est propre.

## Limites connues à communiquer

### Périodes antérieures au 2024-11-01

La règle apprenti s'appuie sur une table interne de SMIC actuellement garantie à partir du `2024-11-01`.

Conséquence :

- pour une DSN dont la date de référence est antérieure au `2024-11-01`, l'outil ne doit pas produire de ventilation apprenti silencieuse ;
- il échoue explicitement au lieu d'appliquer un seuil potentiellement faux.

### Plusieurs contrats apprenti dans le même bloc salarié

Quand un même salarié porte plusieurs contextes de contrat apprenti dans un seul bloc salarié, l'outil ne sait pas encore rattacher chaque cotisation au bon contrat.

Conséquence produit actuelle :

- les lignes apprenti ambiguës sont exclues du split `100 / 726` ;
- le reste du rapprochement continue quand c'est possible ;
- un message explicite doit rester visible dans le produit jusqu'à la mise en place d'un vrai rattachement contrat par contrat.

## Décision produit temporaire

Tant que les sources officielles ne publient pas de table explicite de taux apprenti pour `045 / 068 / 074 / 075`, l'outil réutilise le taux déjà porté par la ligne S81 elle-même pour rejouer le split d'assiette.

Si une source officielle future expose ces taux de façon explicite, cette logique devra être remplacée immédiatement par des constantes métier documentées.
