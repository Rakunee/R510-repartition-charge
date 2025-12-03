import os
import sys
import time
import datetime
import logging
import subprocess
import pymongo

# Configuration
MONGOS_URI = os.environ.get('MONGOS_URI', 'mongodb://localhost:27040')
LOGDIR = os.environ.get('LOGDIR', './logs')
os.makedirs(LOGDIR, exist_ok=True)
LOGFILE = os.path.join(LOGDIR, f"shard_tp_books_{datetime.datetime.now():%Y%m%d_%H%M%S}.log")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[
    logging.FileHandler(LOGFILE, encoding='utf-8'),
    logging.StreamHandler(sys.stdout)
])

logger = logging.getLogger(__name__)

def run_import(port=27040):
    cmd_import = [
        'mongoimport',
        f'--host=localhost',
        f'--port={port}',
        f'--db=tp',
        f'--collection=books',
        f'--file=./Abooks2.json',
        f'--jsonArray'
    ]
    logger.info('Lancement de mongoimport (port=%s)...', port)
    result = subprocess.run(cmd_import, capture_output=True, text=True)
    if result.returncode == 0:
        logger.info('Import réussi')
        return True
    else:
        logger.error('Import échoué: %s', result.stderr.strip())
        return False


def main():
    logger.info('Connexion à mongos: %s', MONGOS_URI)
    client = pymongo.MongoClient(MONGOS_URI, serverSelectionTimeoutMS=5000)
    try:
        # force une sélection du serveur
        client.admin.command('ping')
    except Exception as e:
        logger.error('Impossible de joindre mongos: %s', e)
        sys.exit(2)

    db = client['tp']
    collections = db.list_collection_names()

    if 'books' in collections:
        logger.info("La collection 'books' existe déjà")
    else:
        logger.info("La collection 'books' n'existe pas: import en cours")
        ok = run_import(port=27040)
        if not ok:
            logger.warning('Import KO — continuer quand même vers le sharding si vous le souhaitez')

    # Vérifier si tp.books est déjà sharded
    cfg = client['config']
    collinfo = cfg['collections'].find_one({'_id': 'tp.books'})
    if collinfo and 'key' in collinfo:
        logger.info("La collection 'tp.books' est déjà sharded: clé=%s", collinfo.get('key'))
        return

    # Activer le sharding sur la base
    try:
        logger.info("Activation du sharding pour la base 'tp'...")
        client.admin.command({'enableSharding': 'tp'})
        logger.info('sh.enableSharding OK')
    except Exception as e:
        logger.warning('enableSharding a échoué ou déjà activé: %s', e)

    # Lancer le sharding de la collection sur _id hashed
    # Avant de shard, s'assurer qu'un index commençant par la clé de shard existe
    try:
        logger.info("Vérification des indexes sur tp.books")
        coll = db['books']
        indexes = coll.index_information()
        has_hashed_on_id = False
        for name, info in indexes.items():
            # info['key'] exemple: [('_id', 1)] ou [('_id', 'hashed')]
            keys = info.get('key', [])
            if len(keys) > 0 and keys[0][0] == '_id' and (keys[0][1] == 'hashed' or keys[0][1] == pymongo.HASHED):
                has_hashed_on_id = True
                logger.info("Index hashed sur _id déjà présent: %s", name)
                break

        if not has_hashed_on_id:
            logger.info("Création d'un index hashed sur _id (this may take time)...")
            try:
                coll.create_index([('_id', pymongo.HASHED)])
                logger.info('Index hashed sur _id créé')
            except Exception as ie:
                logger.error('Impossible de créer l\'index hashed sur _id: %s', ie)
                logger.error("Si l'index ne peut pas être créé, envisagez d'utiliser une autre clé de shard ou de vérifier les index existants.")
                sys.exit(5)

    except Exception as e:
        logger.error('Erreur lors de la vérification/creation d\'indexes: %s', e)
        sys.exit(6)

    try:
        logger.info("Shard de la collection 'tp.books' sur {'_id':'hashed'}")
        client.admin.command({'shardCollection': 'tp.books', 'key': {'_id': 'hashed'}})
        logger.info('sh.shardCollection OK')
    except Exception as e:
        logger.error('Erreur shardCollection: %s', e)
        sys.exit(3)

    # Attendre l'apparition des chunks (timeout)
    timeout = 60
    waited = 0
    while waited < timeout:
        cnt = cfg['chunks'].count_documents({'ns': 'tp.books'})
        logger.info('Chunks trouvés pour tp.books: %s', cnt)
        if cnt > 0:
            break
        time.sleep(2)
        waited += 2

    if waited >= timeout:
        logger.warning('Timeout: aucun chunk détecté après %ds', timeout)
        sys.exit(4)

    # Afficher la répartition des chunks par shard
    pipeline = [
        {'$match': {'ns': 'tp.books'}},
        {'$group': {'_id': '$shard', 'count': {'$sum': 1}}}
    ]
    logger.info('Répartition des chunks pour tp.books:')
    for doc in cfg['chunks'].aggregate(pipeline):
        logger.info('Shard %s -> %d chunks', doc['_id'], doc['count'])

    logger.info('Sharding de tp.books terminé avec succès')


if __name__ == '__main__':
    main()




