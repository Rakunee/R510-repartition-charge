// Initialisation du Replica Set B (Shard B)

print("=== Initialisation du Replica Set B ===");
try {
    rs.initiate({
        _id: "replicaSet_b",
        members: [
            { _id: 0, host: "principal_b:27017" },
            { _id: 1, host: "secondaire_b_1:27017" },
            { _id: 2, host: "secondaire_b_2:27017" },
            { _id: 3, host: "secondaire_b_3:27017" }
        ]
    });
    print("Replica Set B initialisé avec succès");
} catch (e) {
    print("Erreur lors de l'initialisation du Replica Set B: " + e);
}