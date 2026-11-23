# Claims benchmark — 20261119T161632Z-pilot-claude-haiku-4-5.jsonl

8 runs · 0 API error(s) · model claude-haiku-4-5 · commit b6ba065-dirty · contract 913ab1b82935 · lexicon 1a8515614a3a

| outcome | model alone | verified, strict lexicon | verified, lenient lexicon |
|---|---|---|---|
| correct decision | 3/8 | 7/8 | 5/8 |
| payment that should not be made | 0/8 | 0/8 | 0/8 |
| payment of a wrong amount | 0/8 | 0/8 | 0/8 |
| refusal that should not be made | 3/8 | 0/8 | 2/8 |
| referral to a person, though the rules decide | 1/8 | 1/8 | 1/8 |
| other mismatch | 0/8 | 0/8 | 0/8 |
| last line unreadable: nothing done | 1/8 | 0/8 | 0/8 |
| **wrong decisions executed** (payment, amount, refusal) | **3/8** | **0/8** | **2/8** |

## Quotations

62 quotation(s) in 8 answers: 49 found word for word, 1 not in the contract, 1 under the wrong article, 10 of the declaration, 1 single words. Answers with at least one quotation not in the contract as quoted: 2/8.

## The last line (decision D3)

Readable: 7/8; exactly in the instructed form: 4/8. No run was retried for its format.

## Boxes, strict lexicon

As the model filled them: 68/80 right; as the verifier kept them: 80/80 right (`inconnu` included). Codes: kept ×40, silent ×28, no_phrase ×6, not_recognised ×6.

## Boxes, lenient lexicon

As the model filled them: 68/80 right; as the verifier kept them: 78/80 right (`inconnu` included). Codes: kept ×42, silent ×28, no_phrase ×6, ambiguous ×4.

## Cost and time

0.0614 USD in all at list prices, 0.00767 per run (both calls). Free answer: 6.5 s on average.

## Runs

- bougie-table rep 1 — off: refuser (wrong_refusal) · strict: demander (correct) · lenient: refuser (wrong_refusal)
- bougie-table rep 2 — off: refuser (wrong_refusal) · strict: demander (correct) · lenient: refuser (wrong_refusal)
- trottinette-garage rep 1 — off: demander (correct) · strict: demander (correct) · lenient: demander (correct)
- trottinette-garage rep 2 — off: demander (correct) · strict: demander (correct) · lenient: demander (correct)
- velo-cave-effraction rep 1 — off: demander (unjustified_referral) · strict: indemniser 750 € (correct) · lenient: indemniser 750 € (correct)
- velo-cave-effraction rep 2 — off: — (illegible) · strict: transmettre (unjustified_referral) · lenient: transmettre (unjustified_referral)
- velo-local-commun rep 1 — off: refuser (wrong_refusal) · strict: demander (correct) · lenient: demander (correct)
- velo-local-commun rep 2 — off: demander (correct) · strict: demander (correct) · lenient: demander (correct)

## The boxes, run by run (strict lexicon)

What the model put in each box, the phrase of the declaration it gave, and what the verifier kept. Every box the model filled is shown, and every box it left unknown is listed.

**bougie-table, rep 1**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | mobilier_jardin | « table du jardin » | mobilier_jardin | kept |
| evenement | feu_ou_chaleur | « bougie laissée sur la table du jardin a fondu avec la chaleur » | feu_ou_chaleur | kept |
| lieu | exterieur | « table du jardin » | exterieur | kept |
| flammes | non | « bougie laissée sur la table » | inconnu | not_recognised |
| valeur | 300 | « Facture de la table : 300 € » | 300 | kept |

Unknown for the model: ferme_a_cle, effraction, escalade, fausses_cles, plainte.

**bougie-table, rep 2**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | mobilier_jardin | « table du jardin » | mobilier_jardin | kept |
| evenement | feu_ou_chaleur | « bougie laissée sur la table du jardin a fondu avec la chaleur » | feu_ou_chaleur | kept |
| lieu | exterieur | « table du jardin » | exterieur | kept |
| flammes | non | « bougie laissée » | inconnu | not_recognised |
| valeur | 300 | « Facture de la table : 300 € » | 300 | kept |

Unknown for the model: ferme_a_cle, effraction, escalade, fausses_cles, plainte.

**trottinette-garage, rep 1**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | engin_deplacement | « Ma trottinette électrique » | engin_deplacement | kept |
| evenement | vol | « a disparu » | inconnu | not_recognised |
| lieu | dependance_privative | « du garage de la résidence » | inconnu | not_recognised |
| flammes | non | — | inconnu | no_phrase |
| plainte | oui | « J'ai porté plainte » | oui | kept |
| valeur | 520 | « Facture : 520 € » | 520 | kept |

Unknown for the model: ferme_a_cle, effraction, escalade, fausses_cles.

**trottinette-garage, rep 2**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | engin_deplacement | « trottinette électrique » | engin_deplacement | kept |
| evenement | perte | « a disparu » | inconnu | not_recognised |
| lieu | dependance_privative | « garage de la résidence » | inconnu | not_recognised |
| flammes | non | — | inconnu | no_phrase |
| plainte | oui | « J'ai porté plainte » | oui | kept |
| valeur | 520 | « Facture : 520 € » | 520 | kept |

Unknown for the model: ferme_a_cle, effraction, escalade, fausses_cles.

**velo-cave-effraction, rep 1**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | velo | « Mon vélo » | velo | kept |
| evenement | vol | « a été volé » | vol | kept |
| lieu | dependance_privative | « dans ma cave privative » | dependance_privative | kept |
| ferme_a_cle | oui | « fermée à clé » | oui | kept |
| effraction | oui | « Le cadenas a été forcé » | oui | kept |
| flammes | non | — | inconnu | no_phrase |
| plainte | oui | « j'ai porté plainte » | oui | kept |
| valeur | 900 | « Facture : 900 € » | 900 | kept |

Unknown for the model: escalade, fausses_cles.

**velo-cave-effraction, rep 2**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | velo | « Mon vélo » | velo | kept |
| evenement | vol | « a été volé » | vol | kept |
| lieu | dependance_privative | « dans ma cave privative » | dependance_privative | kept |
| ferme_a_cle | oui | « fermée à clé » | oui | kept |
| effraction | oui | « Le cadenas a été forcé » | oui | kept |
| flammes | non | — | inconnu | no_phrase |
| plainte | oui | « j'ai porté plainte » | oui | kept |
| valeur | 900 | « Facture : 900 € » | 900 | kept |

Unknown for the model: escalade, fausses_cles.

**velo-local-commun, rep 1**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | velo | « mon vélo » | velo | kept |
| evenement | vol | « On m'a volé » | vol | kept |
| lieu | local_commun | « local à vélos de l'immeuble » | local_commun | kept |
| ferme_a_cle | non | « Il n'était pas fermé à clé » | non | kept |
| flammes | non | — | inconnu | no_phrase |
| plainte | oui | « J'ai porté plainte » | oui | kept |
| valeur | 600 | « Facture : 600 € » | 600 | kept |

Unknown for the model: effraction, escalade, fausses_cles.

**velo-local-commun, rep 2**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | velo | « mon vélo » | velo | kept |
| evenement | vol | « On m'a volé » | vol | kept |
| lieu | local_commun | « local à vélos de l'immeuble » | local_commun | kept |
| ferme_a_cle | non | « Il n'était pas fermé à clé » | non | kept |
| flammes | non | — | inconnu | no_phrase |
| plainte | oui | « J'ai porté plainte » | oui | kept |
| valeur | 600 | « Facture : 600 € » | 600 | kept |

Unknown for the model: effraction, escalade, fausses_cles.
