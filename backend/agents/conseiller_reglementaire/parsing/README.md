# Parsing AMMC avec Docling

Ce dossier contient le debut du pipeline de parsing juridique du recueil AMMC.

## Entrees

- `Recueil_AMMC_VF_ Mars 2026.pdf` : PDF source.
- `notebooks/output/docling_raw.json` : export Docling canonique.
- `notebooks/output/raw_docling.md` : export Markdown utile pour lecture rapide, pas pour parser.

## Pipeline complet

Depuis la racine du projet :

```powershell
$env:PYTHONIOENCODING='utf-8'; python parsing\run_pipeline.py
```

Sorties generees :

- `notebooks/output/normalized_blocks.jsonl`
- `notebooks/output/legal_chunks.jsonl`
- `notebooks/output/validation_report.json`

## Inspection de pages

```powershell
$env:PYTHONIOENCODING='utf-8'; python parsing\docling_normalizer.py --pages 15,33,41,670,763
```

Cette commande sert a verifier l'ordre de lecture reconstruit, notamment les pages en deux colonnes.

## Chunks RAG

`legal_chunks.jsonl` contient des chunks mixtes :

- `article` : chunk principal pour les textes organises en articles.
- `annexe` : chunk pour une annexe sans structure article.
- `annexe_section` : sous-partie d'annexe.
- `annexe_part` : decoupage de securite pour les annexes trop longues.

## Validation

```powershell
$env:PYTHONIOENCODING='utf-8'; python parsing\validate_chunks.py
```

Le validateur signale :

- chunks vides ;
- articles sans document ;
- plages de pages invalides ;
- chunks trop longs ;
- sauts suspects dans la numerotation des articles.

Les sauts d'articles ne sont pas forcement des erreurs : dans un recueil juridique consolide, ils peuvent venir d'articles abroges, de renvois, de reprises ou de structures internes.
