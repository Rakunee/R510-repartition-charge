// Script d'initialisation des replica sets pour MongoDB Sharded Cluster

// Ce script doit être exécuté sur chaque replica set

// Pour le config server (à exécuter sur config_server_1)
// mongosh --host config_server_1:27017 --file init-replica-sets.js

print("=== Initialisation du Config Replica Set ===");
try {
    rs.initiate({
        _id: "configReplSet",
        configsvr: true,
        members: [
            { _id: 0, host: "config_server_1:27017" },
            { _id: 1, host: "config_server_2:27017" },
            { _id: 2, host: "config_server_3:27017" }
        ]
    });
    print("Config Replica Set initialisé avec succès");
} catch (e) {
    print("Erreur lors de l'initialisation du Config Replica Set: " + e);
}