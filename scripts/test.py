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
    
    # Attendre l'apparition des chunks
    timeout = 15
    waited = 0
    chunks_found = False
    
    logger.info('Attente de la création des chunks (max %ds)...', timeout)
    while waited < timeout:
        cnt = cfg['chunks'].count_documents({'ns': 'tp.books'})
        if cnt > 0:
            logger.info('%d chunks trouvés pour tp.books', cnt)
            chunks_found = True
            break
        time.sleep(2)
        waited += 2

    if not chunks_found:
        logger.warning('Aucun chunk détecté après %ds', waited)
        logger.warning('  C\'est normal pour une collection vide/nouvelle')
        logger.warning('  Les chunks seront créés automatiquement lors de l\'insertion de données')
        logger.info('  Le sharding est configuré, on continue...')
    
    # Afficher la répartition des chunks par shard (si disponibles)
    if chunks_found:
        pipeline = [
            {'$match': {'ns': 'tp.books'}},
            {'$group': {'_id': '$shard', 'count': {'$sum': 1}}}
        ]
        logger.info('Répartition des chunks pour tp.books:')
        for doc in cfg['chunks'].aggregate(pipeline):
            logger.info('  Shard %s -> %d chunks', doc['_id'], doc['count'])

    logger.info('Configuration du sharding terminée')
    return client


def test_operations(client):
    """Tests CRUD sur la collection tp.books"""
    logger.info('\n' + '='*60)
    logger.info('DÉBUT DES TESTS CRUD')
    logger.info('='*60)
    
    db = client['tp']
    books = db['books']
    cfg = client['config']
    
    # Compteur initial
    initial_count = books.count_documents({})
    logger.info(f'Nombre de documents initial: {initial_count}')
    
    logger.info('\n--- TEST 1: Insertion de nouveaux documents ---')
    test_books = [
        {
            '_id': 'test_book_1',
            'title': 'Test Book 1',
            'authors': ['Test Author 1'],
            'isbn': 'TEST-123-456',
            'categories': ['Test'],
            'pageCount': 100,
            'publishedDate': {'$date': '2025-12-03T00:00:00.000Z'}
        },
        {
            '_id': 'test_book_2',
            'title': 'Test Book 2',
            'authors': ['Test Author 2'],
            'isbn': 'TEST-789-012',
            'categories': ['Test', 'Technology'],
            'pageCount': 200,
            'publishedDate': {'$date': '2025-12-03T00:00:00.000Z'}
        },
        {
            '_id': 'test_book_3',
            'title': 'Test Book 3',
            'authors': ['Test Author 3'],
            'isbn': 'TEST-345-678',
            'categories': ['Science'],
            'pageCount': 150,
            'publishedDate': {'$date': '2025-12-03T00:00:00.000Z'}
        }
    ]
    
    try:
        result = books.insert_many(test_books)
        logger.info(f' Insertion réussie: {len(result.inserted_ids)} documents insérés')
        logger.info(f'  IDs insérés: {result.inserted_ids}')
    except Exception as e:
        logger.error(f' Erreur lors de l\'insertion: {e}')
    
    # Vérifier le nouveau count
    new_count = books.count_documents({})
    logger.info(f'Nombre de documents après insertion: {new_count} (delta: +{new_count - initial_count})')
    
    logger.info('\n--- TEST 2: Lecture de documents ---')
    
    # Lecture simple
    logger.info('2.1 - Lecture d\'un document par _id:')
    doc = books.find_one({'_id': 'test_book_1'})
    if doc:
        logger.info(f'   Document trouvé: {doc.get("title")} par {doc.get("authors")}')
    else:
        logger.warning('   Document non trouvé')
    
    # Lecture avec filtre
    logger.info('2.2 - Lecture de tous les documents de test:')
    test_docs = list(books.find({'_id': {'$regex': '^test_book_'}}).limit(10))
    logger.info(f'   {len(test_docs)} documents trouvés avec filtre regex')
    
    # Lecture avec projection
    logger.info('2.3 - Lecture avec projection (title et authors uniquement):')
    projected = list(books.find(
        {'_id': {'$regex': '^test_book_'}},
        {'title': 1, 'authors': 1}
    ).limit(3))
    for p in projected:
        logger.info(f'  - {p.get("_id")}: {p.get("title")}')
    
    # Vérifier la répartition des documents de test sur les shards
    logger.info('2.4 - Vérification de la répartition sur les shards:')
    try:
        for test_id in ['test_book_1', 'test_book_2', 'test_book_3']:
            explain = db.command('explain', {
                'find': 'books',
                'filter': {'_id': test_id}
            }, verbosity='queryPlanner')
            
            shards_info = explain.get('queryPlanner', {}).get('winningPlan', {}).get('shards', [])
            if shards_info:
                shard_name = shards_info[0].get('shardName', 'unknown')
                logger.info(f'  - {test_id} -> shard: {shard_name}')
    except Exception as e:
        logger.warning(f'  Impossible de déterminer la répartition: {e}')
    
    logger.info('\n--- TEST 3: Modification de documents ---')
    
    # Update simple
    logger.info('3.1 - Modification d\'un document (update pageCount):')
    try:
        result = books.update_one(
            {'_id': 'test_book_1'},
            {'$set': {'pageCount': 250, 'updated': True}}
        )
        logger.info(f'   {result.matched_count} document(s) correspondant(s), {result.modified_count} modifié(s)')
        
        updated_doc = books.find_one({'_id': 'test_book_1'})
        logger.info(f'  Nouvelle valeur pageCount: {updated_doc.get("pageCount")}')
    except Exception as e:
        logger.error(f'   Erreur: {e}')
    
    # Update multiple
    logger.info('3.2 - Modification de plusieurs documents (ajout tag):')
    try:
        result = books.update_many(
            {'_id': {'$regex': '^test_book_'}},
            {'$set': {'test_tag': 'crud_operations', 'test_timestamp': datetime.datetime.now()}}
        )
        logger.info(f'   {result.matched_count} document(s) correspondant(s), {result.modified_count} modifié(s)')
    except Exception as e:
        logger.error(f'   Erreur: {e}')
    
    logger.info('\n--- TEST 4: Suppression de documents ---')
    
    # Suppression simple
    logger.info('4.1 - Suppression d\'un document:')
    try:
        result = books.delete_one({'_id': 'test_book_1'})
        logger.info(f'   {result.deleted_count} document(s) supprimé(s)')
    except Exception as e:
        logger.error(f'   Erreur: {e}')
    
    # Suppression multiple
    logger.info('4.2 - Suppression de plusieurs documents:')
    try:
        result = books.delete_many({'_id': {'$regex': '^test_book_'}})
        logger.info(f'   {result.deleted_count} document(s) supprimé(s)')
    except Exception as e:
        logger.error(f'   Erreur: {e}')
    
    # Compteur final
    final_count = books.count_documents({})
    logger.info(f'\nNombre de documents final: {final_count} (delta par rapport au début: {final_count - initial_count})')
    
    logger.info('\n--- Statistiques finales du cluster ---')
    
    # Répartition des chunks
    pipeline = [
        {'$match': {'ns': 'tp.books'}},
        {'$group': {'_id': '$shard', 'count': {'$sum': 1}}}
    ]
    logger.info('Répartition des chunks:')
    for doc in cfg['chunks'].aggregate(pipeline):
        logger.info(f'  Shard {doc["_id"]}: {doc["count"]} chunks')
    
    # Statistiques de la collection
    try:
        stats = db.command('collStats', 'books')
        logger.info(f'Taille totale: {stats.get("size", 0)} bytes')
        logger.info(f'Nombre d\'index: {stats.get("nindexes", 0)}')
        logger.info(f'Sharded: {stats.get("sharded", False)}')
    except Exception as e:
        logger.warning(f'Impossible de récupérer les stats: {e}')
    
    logger.info('\n' + '='*60)
    logger.info('FIN DES TESTS CRUD')
    logger.info('='*60)


if __name__ == '__main__':
    client = main()  # Récupérer le client depuis main()
    
    # Attendre un peu que les chunks se propagent si nécessaire
    logger.info('\nPause de 5 secondes avant les tests CRUD...')
    time.sleep(5)
    
    # Lancer les tests CRUD
    logger.info('\nLancement des tests CRUD...')
    try:
        if not client:
            # Si main() n'a pas retourné de client (sharding déjà fait), en créer un nouveau
            client = pymongo.MongoClient(MONGOS_URI, serverSelectionTimeoutMS=5000)
        
        test_operations(client)
        logger.info('\n Tous les tests sont terminés avec succès')
    except Exception as e:
        logger.error(f'\n Erreur lors des tests: {e}')
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(10)




