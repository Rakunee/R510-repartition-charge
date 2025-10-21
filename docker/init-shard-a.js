// Initialisation du Replica Set A (Shard A)

print("=== Initialisation du Replica Set A ===");
try {
    rs.initiate({
        _id: "replicaSet_a",
        members: [
            { _id: 0, host: "principal_a:27017" },
            { _id: 1, host: "secondaire_a_1:27017" },
            { _id: 2, host: "secondaire_a_2:27017" },
            { _id: 3, host: "secondaire_a_3:27017" }
        ]
    });
    print("Replica Set A initialisé avec succès");
} catch (e) {
    print("Erreur lors de l'initialisation du Replica Set A: " + e);
}