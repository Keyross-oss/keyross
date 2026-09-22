# Le workflow IA compilable — manifeste
### *Compilable AI Workflows — compile the output, not just the plan*

v0.1 · septembre 2026 · Wassim Amri — Keyross

## 1. Le constat

Claude Code est fiable. Pas parce que son modèle est meilleur — parce que le code a un **compilateur**, des **tests** et une **CI** : des oracles gratuits, déterministes, immédiats, qui disent après chaque action si le résultat est juste. Les agents de code ont hérité de quarante ans d'outillage de vérification sans avoir eu à l'écrire.

Les agents métier n'ont rien de tout ça. Un devis, une facture, un décompte de sinistre, un dossier KYC n'ont ni compilateur ni tests. Alors on vérifie avec le modèle lui-même — un juge probabiliste qui note un producteur probabiliste — et on s'étonne que ça ne tienne pas en production.

En 2026, les agents ont appris à compiler leurs plans : une intention devient un plan d'exécution déterministe, rejouable, auditable. C'est la bonne moitié. **Personne ne compile leurs résultats.** Ce manifeste est l'autre moitié.

## 2. La définition

Un **compilateur métier** est un programme déterministe qui prend un artefact métier et ses référentiels, et rend un verdict structuré avec ses preuves. Il a quatre composants :

- le **schéma** — les types : une quantité est un nombre, une unité appartient à un vocabulaire ;
- les **invariants** — ce qui est vrai quel que soit le plan : le total égale la somme des lignes, aucune ligne chiffrée ne disparaît ;
- les **contrats par action** — ce qui est vrai si l'action a fait ce qu'elle annonçait, instancié avec les paramètres du plan ;
- les **référentiels** — le *linker* : le tarif, la nomenclature, le lexique, fournis par le client.

Il a deux passes : la première **compile le plan** (les pré-conditions, avant de toucher quoi que ce soit), la seconde **compile le résultat** (les post-conditions et les invariants, après chaque action et à la gate). Un workflow est **compilable** quand ses résultats ont un compilateur.

Ce qu'il n'est pas : un LLM-juge, un moteur de règles de décision, un workflow compilé — ni un skill, un prompt ou un fichier d'instructions : un compilateur est du code qu'un modèle ne lit jamais, avec des règles que le modèle ne voit jamais. Il compile le document, comme gcc compile le code ; l'agent est le développeur.

## 3. Les dix principes

1. **Déterministe ou rien.** Un oracle a raison ou tort ; il ne pense pas. Un vérificateur probabiliste est nommé comme tel et n'est jamais la fonction de récompense.
2. **Écrit par des humains, jamais appris.** Un oracle qui apprend n'est plus un oracle. La suite d'oracles s'améliore par versions, après revue humaine, sur des propositions fondées sur des preuves.
3. **Invisible à l'agent, exécuté par le harness.** L'oracle n'est ni dans le prompt, ni dans la liste d'outils, ni dans un fichier lisible. Le modèle ne rapporte jamais un vert ; il ne peut donc pas en fabriquer un.
4. **Retour minimal suffisant.** L'agent reçoit rouge ou vert et la catégorie de l'écart — assez pour corriger, pas assez pour contourner.
5. **Rejoué hors de l'agent.** La gate rejoue la suite complète depuis un environnement neuf. Vert de l'agent et rouge de la gate : un incident d'intégrité, pas une note.
6. **Redondant, avec sentinelles.** La même propriété vue par plusieurs oracles indépendants ; des oracles silencieux, à poids nul, qui signent un contournement.
7. **Testé lui-même.** Chaque oracle a son cas faux ; un oracle qui ne rougit plus jamais est mort, pas bon.
8. **Versionné, épinglé, journalisé.** Chaque run sait quels oracles l'ont vérifié. C'est la preuve pour l'audit.
9. **Écrit avant le premier agent.** Sans compilateur, aucune boucle ne peut être fiable — ni apprendre. La première question d'un projet d'agent : *quel est votre compilateur ?*
10. **Ouvert.** Le format du verdict, le registre et le cycle de vie sont publics ; les gauges sectoriels sont l'accumulation des terrains.

## 4. L'architecture minimale

Un registre d'oracles versionnés, packagés en gauges et installables depuis un seul endroit · un runner qui les exécute et rend un rapport et un exit code · une gate qui rejoue tout hors de l'agent · un lock qui épingle · une calibration qui confronte, plus tard, les oracles à la vérité terrain. Trois expositions : une bibliothèque, une ligne de commande, un serveur MCP que n'importe quel harness appelle.

Sa relation à l'apprentissage : le compilateur est la fonction de récompense. La politique apprend — quelle action préférer parmi celles qui sont permises. Le compilateur, jamais.

## 5. Les conditions d'un domaine compilable

Un artefact structuré ou structurable, sur lequel des opérations fermées existent · un oracle structurel bon marché — un compilateur — qui existe ou peut être écrit · des actions nommables, pour dériver des contrats · un sandbox et un diff attribuable à une tâche · un coût d'erreur élevé · une vérité terrain rare mais existante, pour calibrer · et la stationnarité : des règles qui changent en années, pas en semaines.

## 6. Le cycle de vie

Proposer (un humain, ou l'agent avec ses cas) → revoir → approuver → versionner → épingler → calibrer → retirer. Le client possède ses oracles ; le moteur et les gauges généralisés restent ouverts.

## 7. Ce qui existe, et où ceci se place

Les agents compilent leurs plans (Compiled AI, les agent compilers) ; les plateformes régulées compilent des politiques en vérifications déterministes, en fermé ; les outils de fiabilité évaluent avec des juges génériques ; les couches de vérification du code existent pour le code. Ce manifeste occupe la case vide : **le compilateur de l'artefact métier, ouvert, sectoriel, calibré, avec une gate.**

## 8. Ce que ce manifeste demande

Écrivez le compilateur avant l'agent. Publiez vos invariants. Contribuez un gauge.

*Apache-2.0 — keyross.*
