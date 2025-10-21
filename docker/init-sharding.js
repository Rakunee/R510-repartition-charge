// Script d'ajout des shards au cluster
// À exécuter sur un routeur (mongos)

print("=== Ajout des shards au cluster ===");

try {
    sh.addShard("replicaSet_a/principal_a:27017,secondaire_a_1:27017,secondaire_a_2:27017,secondaire_a_3:27017");
    print("Shard A ajouté avec succès");
} catch (e) {
    print("Erreur lors de l'ajout du Shard A: " + e);
}

try {
    sh.addShard("replicaSet_b/principal_b:27017,secondaire_b_1:27017,secondaire_b_2:27017,secondaire_b_3:27017");
    print("Shard B ajouté avec succès");
} catch (e) {
    print("Erreur lors de l'ajout du Shard B: " + e);
}

try {
    sh.addShard("replicaSet_c/principal_c:27017,secondaire_c_1:27017,secondaire_c_2:27017,secondaire_c_3:27017");
    print("Shard C ajouté avec succès");
} catch (e) {
    print("Erreur lors de l'ajout du Shard C: " + e);
}

print("=== Vérification du statut du sharding ===");
sh.status();