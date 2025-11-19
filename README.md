# POK 1 - git

## Fonctionnement de git

### Object Database (dossier .git/objects)

Tous les objets sont constitués d'un header et de données, séparées par un NUL character.
Le header contient le type de l'objet et la longueur des données.

#### BLOB

Un "blob" représente un fichier.

```a
blob {content length}{NUL byte}{data}
```

#### TREE

Un "tree" représente un dossier, il peut contenir d'autres objets "tree"

```a
tree {content length}{NUL byte}
{mode} {path}{NUL byte}{hash}
{mode} {path}{NUL byte}{hash}
{mode} {path}{NUL byte}{hash}

```

#### CHANGESET

Un "changeset" représente un commit

```a
changeset {content length}{NUL byte}
tree {hash}
parent {hash}
author Jean Loutre jean.loutre@centrale-med.fr
commiter Jean Loutre jean.loutre@centrale-med.fr

{commit message}

```

### git index

L'index est une liste d'objets représentant tous les fichiers contenus dans le dossier dans leur état au moment de la commande add.
L'index stocke aussi des métadonnées sur les fichiers traqués:

- ctime_s : Change time (en s), le temps où les métadonnées du fichier ont changé pour la dernière fois
- ctime_n : Change time (en ns), la partie fractionnaire du Change time
- mtime_s : Modification time (en s), le temps où le contenu du fichier a changé pour la dernière fois
- mtime_n : Modification time (en ns), la partie fractionnaire du Modification time
- dev : le device sur lequel le fichier est
- ino : inode number
- mode : le mode (unix) du fichier
- uid : L'id de l'user propriétaire du fichier
- gid : L'id du groupe propriétaire du fichier
- size
- sha1 : le nom du blob qui représente le fichier
- flags
- path
