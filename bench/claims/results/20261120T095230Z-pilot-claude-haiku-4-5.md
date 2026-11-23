# Claims benchmark — 20261120T095230Z-pilot-claude-haiku-4-5.jsonl

8 runs · 0 API error(s) · model claude-haiku-4-5 · commit b6ba065-dirty · contract 47561e08bae8 · lexicon 68d7aebcdcf8 · prompts bee543dd2a5d

## The four arms

Two instructions, without and with the verifier (strict lexicon). A wrong decision executed is a payment that should not be made, a payment of a wrong amount, or a refusal that should not be made. The two arms of an instruction read the same answer.

| | wrong decisions executed | correct decisions | sent to a person, though the rules decide |
|---|---|---|---|
| model alone, base instruction | **4/8** | 3/8 | 1/8 |
| model alone, reinforced instruction | **4/8** | 4/8 | 0/8 |
| with the verifier, base instruction | **0/8** | 7/8 | 1/8 |
| with the verifier, reinforced instruction | **0/8** | 7/8 | 1/8 |

## Outcomes in detail

| outcome | alone · base | alone · reinforced | verifier · base | verifier · reinforced |
|---|---|---|---|---|
| correct decision | 3/8 | 4/8 | 7/8 | 7/8 |
| payment that should not be made | 0/8 | 0/8 | 0/8 | 0/8 |
| payment of a wrong amount | 0/8 | 0/8 | 0/8 | 0/8 |
| refusal that should not be made | 4/8 | 4/8 | 0/8 | 0/8 |
| referral to a person, though the rules decide | 1/8 | 0/8 | 1/8 | 1/8 |
| other mismatch | 0/8 | 0/8 | 0/8 | 0/8 |
| last line unreadable: nothing done | 0/8 | 0/8 | 0/8 | 0/8 |

## By case

Correct decisions out of the runs of each case, the others by kind.

| case | expected | alone · base | alone · reinforced | verifier · base | verifier · reinforced |
|---|---|---|---|---|---|
| velo-local-commun | indetermine · demander | 0/2 (refusal 2) | 0/2 (refusal 2) | 2/2 | 2/2 |
| bougie-table | indetermine · demander | 0/2 (refusal 2) | 0/2 (refusal 2) | 2/2 | 2/2 |
| trottinette-garage | indetermine · demander | 2/2 | 2/2 | 2/2 | 2/2 |
| velo-cave-effraction | couvert · indemniser 750 € | 1/2 (referral 1) | 2/2 | 1/2 (referral 1) | 1/2 (referral 1) |

## The lenient lexicon

The same outputs, verified with the lenient lexicon: a value is also kept when no listed expression backs it, unless a negation, a doubt or an ambiguous expression listed against it is there.

| | wrong decisions executed | correct decisions | sent to a person, though the rules decide |
|---|---|---|---|
| with the verifier, base instruction | **2/8** | 5/8 | 1/8 |
| with the verifier, reinforced instruction | **2/8** | 5/8 | 1/8 |

## The verifier's journal

What the verifier wrote down in these runs, judged against the labels written before the run: its limits and its edge cases, kept on purpose. A value refused though the declaration states it is a wording the lexicon lacks: it goes to the calibration list. The whole journal, one entry per line, goes with the results.

| the boxes, as the verifier left them | strict | lenient |
|---|---|---|
| refused, though the declaration states it: a wording the lexicon lacks | 2 | 2 |
| kept, though the declaration does not state it | 0 | 2 |
| refused, rightly: the declaration does not state it | 12 | 10 |
| left unknown by the model, though the declaration states it | 0 | 0 |

### The calibration list

- trottinette-garage · `valeur = 520` from « 520 € » · not_justified, strict · 1× (run 2)
- trottinette-garage · `valeur = 520` from « 520 € » · not_justified, lenient · 1× (run 2)
- velo-cave-effraction · `valeur = 900` from « 900 € » · not_justified, strict · 1× (run 1)
- velo-cave-effraction · `valeur = 900` from « 900 € » · not_justified, lenient · 1× (run 1)

### Kept against the labels

- bougie-table · `flammes = non` from « bougie laissée », where the label says `inconnu` · lenient · 1× (run 1)
- bougie-table · `flammes = non` from « bougie laissée sur la table », where the label says `inconnu` · lenient · 1× (run 2)

### The verifier's decisions that differ from the expected answer

- bougie-table · base instruction · lenient · refuser (wrong_refusal, executed) · agreement: model non_couvert, rules non_couvert; boxes kept wrong: flammes · 2× (runs 1, 2)
- bougie-table · reinforced instruction · lenient · refuser (wrong_refusal, executed) · agreement: model non_couvert, rules non_couvert; boxes kept wrong: flammes · 2× (runs 1, 2)
- velo-cave-effraction · base instruction · strict · demander (unjustified_referral) · agreement: model couvert, rules couvert; boxes kept wrong: valeur · 1× (run 1)
- velo-cave-effraction · base instruction · lenient · demander (unjustified_referral) · agreement: model couvert, rules couvert; boxes kept wrong: valeur · 1× (run 1)
- velo-cave-effraction · reinforced instruction · strict · demander (unjustified_referral) · agreement: model couvert, rules couvert; boxes kept wrong: valeur · 1× (run 1)
- velo-cave-effraction · reinforced instruction · lenient · demander (unjustified_referral) · agreement: model couvert, rules couvert; boxes kept wrong: valeur · 1× (run 1)

### Refusals, one by one

By the model alone, each with the reason it gave:

- bougie-table, run 1, base instruction · refused · wrong · articles named: 2, 4.1, 4.3, 6.1, 6.5, 7.1 — « Conclusion Le sinistre ne bénéficie d'aucune garantie applicable : le mobilier de jardin n'est garanti que contre l'incendie, la tempête et la grêle (article 4.3), et l'exclusion de l'article 6.5 couvre spécifiquement les dommages par chaleur sans embrasement. »
- bougie-table, run 1, reinforced instruction · refused · wrong · articles named: 1, 2, 4.3, 6.5 — « Conclusion : Le mobilier de jardin bénéficie d'une couverture limitée à trois risques (incendie, tempête, grêle). Le dommage décrit résulte de la chaleur sans embrasement, ce qui entre dans l'exclusion de l'article 6.5. Même si l'exclusion de l'article 6.5 ne mentionnait pas spécifiquement le mobilier de jardin, le cumul des articles 4.3 et 6.5 fait que ce sinistre n'est pas couvert : il n'est ni… »
- bougie-table, run 2, base instruction · refused · wrong · articles named: 2, 4.1, 4.3, 6.5, 7.1 — « Le sinistre n'est couvert par aucune garantie applicable. L'exclusion de l'article 6.5 s'oppose à l'indemnisation. »
- bougie-table, run 2, reinforced instruction · refused · wrong · articles named: 1, 2, 4.1, 4.3, 6.1, 6.5 — « Conclusion Bien que le mobilier de jardin soit assuré et le sinistre déclaré à temps, le dommage résulte d'une action de chaleur sans embrasement, ce qui est explicitement exclu par l'article 6.5. De plus, même si l'incendie avait été applicable, seul l'incendie est garanti pour le mobilier de jardin (article 4.3), et ce sinistre n'en constitue pas un. »
- velo-local-commun, run 1, base instruction · refused · wrong · articles named: 1, 2, 3, 4.2, 6.3, 7.2 — « Malgré le respect de ces conditions, l'exclusion de l'article 6.3 rend le sinistre non couvert. »
- velo-local-commun, run 1, reinforced instruction · refused · wrong · articles named: 2, 3, 4.2, 6.3, 7.1, 7.2 — « Bien que le bien (vélo) soit assuré et le vol se soit produit dans un local assuré (local commun), l'article 6.3 exclut spécifiquement les vols « commis sans effraction dans un local commun non fermé ». Le local à vélos n'était pas fermé à clé, et il n'y a eu aucune effraction. Cette exclusion s'applique et fait obstacle au versement d'une indemnité. »
- velo-local-commun, run 2, base instruction · refused · wrong · articles named: 1, 2, 3, 4.2, 6.3 — « Bien que le vol soit en principe un sinistre garanti et que le vélo soit un bien assuré, l'exclusion de l'article 6.3 s'applique car il s'agit d'un vol sans effraction dans un local commun non fermé. »
- velo-local-commun, run 2, reinforced instruction · refused · wrong · articles named: 1, 2, 4.2, 6.3 — « Le sinistre ne satisfait pas aux conditions de la garantie vol (absence d'effraction) ET rentre dans une exclusion explicite (article 6.3). »

By the verifier:

- bougie-table · base instruction · lenient · refused under 6.5 · wrong · 2× (runs 1, 2)
- bougie-table · reinforced instruction · lenient · refused under 6.5 · wrong · 2× (runs 1, 2)

## Quotations

**Base instruction.** 54 quotation(s) in 8 answers: 44 found word for word, 2 not in the contract (1 of them close to a passage: a paraphrase in quotes; the others invented), 0 under the wrong article, 6 of the declaration, 2 single word(s). Answers with at least one quotation not in the contract as quoted: 1/8.

**Reinforced instruction.** 66 quotation(s) in 8 answers: 53 found word for word, 1 not in the contract (1 of them close to a passage: a paraphrase in quotes; the others invented), 0 under the wrong article, 11 of the declaration, 1 single word(s). Answers with at least one quotation not in the contract as quoted: 1/8.

## The last line (decision D3)

- Base instruction: readable 8/8; exactly in the instructed form 5/8.
- Reinforced instruction: readable 8/8; exactly in the instructed form 7/8.

No run was retried for its format.

## Boxes, strict lexicon

As the model filled them: 68/80 right; as the verifier kept them: 78/80 right (`inconnu` included). Codes: kept ×38, silent ×28, no_phrase ×6, not_recognised ×6, not_justified ×2. One extraction per run serves both instructions: it reads neither answer.

## Boxes, lenient lexicon

As the model filled them: 68/80 right; as the verifier kept them: 76/80 right (`inconnu` included). Codes: kept ×40, silent ×28, no_phrase ×6, ambiguous ×4, not_justified ×2.

## Cost and time

0.1021 USD in all at list prices, 0.01276 per run (all its calls). Free answer, on average: base instruction 6.7 s, reinforced instruction 6.9 s.

## Runs

- bougie-table rep 1 — base: off refuser (wrong_refusal) · strict demander (correct) · lenient refuser (wrong_refusal) | reinforced: off refuser (wrong_refusal) · strict demander (correct) · lenient refuser (wrong_refusal)
- bougie-table rep 2 — base: off refuser (wrong_refusal) · strict demander (correct) · lenient refuser (wrong_refusal) | reinforced: off refuser (wrong_refusal) · strict demander (correct) · lenient refuser (wrong_refusal)
- trottinette-garage rep 1 — base: off demander (correct) · strict demander (correct) · lenient demander (correct) | reinforced: off demander (correct) · strict demander (correct) · lenient demander (correct)
- trottinette-garage rep 2 — base: off demander (correct) · strict demander (correct) · lenient demander (correct) | reinforced: off demander (correct) · strict demander (correct) · lenient demander (correct)
- velo-cave-effraction rep 1 — base: off indemniser 750 € (correct) · strict demander (unjustified_referral) · lenient demander (unjustified_referral) | reinforced: off indemniser 750 € (correct) · strict demander (unjustified_referral) · lenient demander (unjustified_referral)
- velo-cave-effraction rep 2 — base: off demander (unjustified_referral) · strict indemniser 750 € (correct) · lenient indemniser 750 € (correct) | reinforced: off indemniser 750 € (correct) · strict indemniser 750 € (correct) · lenient indemniser 750 € (correct)
- velo-local-commun rep 1 — base: off refuser (wrong_refusal) · strict demander (correct) · lenient demander (correct) | reinforced: off refuser (wrong_refusal) · strict demander (correct) · lenient demander (correct)
- velo-local-commun rep 2 — base: off refuser (wrong_refusal) · strict demander (correct) · lenient demander (correct) | reinforced: off refuser (wrong_refusal) · strict demander (correct) · lenient demander (correct)

## The boxes, run by run (strict lexicon)

What the model put in each box, the phrase of the declaration it gave, and what the verifier kept. Every box the model filled is shown, and every box it left unknown is listed.

**bougie-table, rep 1**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | mobilier_jardin | « table du jardin » | mobilier_jardin | kept |
| evenement | feu_ou_chaleur | « bougie laissée sur la table du jardin a fondu avec la chaleur » | feu_ou_chaleur | kept |
| lieu | exterieur | « table du jardin » | exterieur | kept |
| flammes | non | « bougie laissée » | inconnu | not_recognised |
| valeur | 300 | « Facture de la table : 300 € » | 300 | kept |

Unknown for the model: ferme_a_cle, effraction, escalade, fausses_cles, plainte.

**bougie-table, rep 2**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | mobilier_jardin | « table du jardin » | mobilier_jardin | kept |
| evenement | feu_ou_chaleur | « bougie laissée sur la table du jardin a fondu avec la chaleur » | feu_ou_chaleur | kept |
| lieu | exterieur | « table du jardin » | exterieur | kept |
| flammes | non | « bougie laissée sur la table » | inconnu | not_recognised |
| valeur | 300 | « Facture de la table : 300 € » | 300 | kept |

Unknown for the model: ferme_a_cle, effraction, escalade, fausses_cles, plainte.

**trottinette-garage, rep 1**

| box | the model's value | its phrase | kept | why |
|---|---|---|---|---|
| bien | engin_deplacement | « Ma trottinette électrique » | engin_deplacement | kept |
| evenement | perte | « a disparu » | inconnu | not_recognised |
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
| valeur | 520 | « 520 € » | inconnu | not_justified |

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
| valeur | 900 | « 900 € » | inconnu | not_justified |

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
