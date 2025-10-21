// Initialisation du Replica Set C (Shard C)

print("=== Initialisation du Replica Set C ===");
try {
    rs.initiate({
        _id: "replicaSet_c",
        members: [
            { _id: 0, host: "principal_c:27017" },
            { _id: 1, host: "secondaire_c_1:27017" },
            { _id: 2, host: "secondaire_c_2:27017" },
            { _id: 3, host: "secondaire_c_3:27017" }
        ]
    });
    print("Replica Set C initialisé avec succès");
} catch (e) {
    print("Erreur lors de l'initialisation du Replica Set C: " + e);
}