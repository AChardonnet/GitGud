# POK 1 - git

## Fonctionnement de git

### Object Database (dossier .git/objects)

Tous les objets sont constitués d'un header et de données, séparées par un NUL character.
Le header contient le type de l'objet et la longueur des données.

#### BLOB

Un "blob" représente un fichier.

```python
blob {content length}{NUL byte}{data}
```

#### TREE

Un "tree" représente un dossier, il peut contenir d'autres objets "tree"

```python
tree {content length}{NUL byte}{mode} {path}{NUL byte}{hash}
{mode} {path}{NUL byte}{hash}
{mode} {path}{NUL byte}{hash}

```

#### CHANGESET

Un "changeset" représente un commit

```python
changeset {content length}{NUL byte}tree {hash}
parent {hash}
author Jean Loutre jean.loutre@centrale-med.fr
commiter Jean Loutre jean.loutre@centrale-med.fr

{commit message}

```

### Current directory cache

Stocke un état du dossier à un moment donné.
