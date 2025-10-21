# Script PowerShell pour initialiser le cluster MongoDB Sharded
Write-Host "=== Configuration du Cluster MongoDB Sharded ===" -ForegroundColor Green

# Attendre que les conteneurs soient prêts
Write-Host "`nAttente du démarrage des conteneurs (30 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# 1. Initialiser le Config Server Replica Set
Write-Host "`n1. Initialisation du Config Server Replica Set..." -ForegroundColor Cyan
docker exec -it config_server_1 mongosh --eval "
rs.initiate({
    _id: 'configReplSet',
    configsvr: true,
    members: [
        { _id: 0, host: 'config_server_1:27017' },
        { _id: 1, host: 'config_server_2:27017' },
        { _id: 2, host: 'config_server_3:27017' }
    ]
})
"

Write-Host "`nAttente de l'élection du primary du config server (10 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 2. Initialiser Shard A
Write-Host "`n2. Initialisation du Shard A (replicaSet_a)..." -ForegroundColor Cyan
docker exec -it principal_a mongosh --eval "
rs.initiate({
    _id: 'replicaSet_a',
    members: [
        { _id: 0, host: 'principal_a:27017' },
        { _id: 1, host: 'secondaire_a_1:27017' },
        { _id: 2, host: 'secondaire_a_2:27017' },
        { _id: 3, host: 'secondaire_a_3:27017' }
    ]
})
"

Write-Host "`nAttente de l'élection du primary du shard A (10 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 3. Initialiser Shard B
Write-Host "`n3. Initialisation du Shard B (replicaSet_b)..." -ForegroundColor Cyan
docker exec -it principal_b mongosh --eval "
rs.initiate({
    _id: 'replicaSet_b',
    members: [
        { _id: 0, host: 'principal_b:27017' },
        { _id: 1, host: 'secondaire_b_1:27017' },
        { _id: 2, host: 'secondaire_b_2:27017' },
        { _id: 3, host: 'secondaire_b_3:27017' }
    ]
})
"

Write-Host "`nAttente de l'élection du primary du shard B (10 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 4. Initialiser Shard C
Write-Host "`n4. Initialisation du Shard C (replicaSet_c)..." -ForegroundColor Cyan
docker exec -it principal_c mongosh --eval "
rs.initiate({
    _id: 'replicaSet_c',
    members: [
        { _id: 0, host: 'principal_c:27017' },
        { _id: 1, host: 'secondaire_c_1:27017' },
        { _id: 2, host: 'secondaire_c_2:27017' },
        { _id: 3, host: 'secondaire_c_3:27017' }
    ]
})
"

Write-Host "`nAttente de l'élection du primary du shard C (10 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 5. Ajouter les shards au cluster
Write-Host "`n5. Ajout des shards au cluster via le routeur..." -ForegroundColor Cyan
docker exec -it routeur_1 mongosh --eval "
sh.addShard('replicaSet_a/principal_a:27017,secondaire_a_1:27017,secondaire_a_2:27017,secondaire_a_3:27017');
sh.addShard('replicaSet_b/principal_b:27017,secondaire_b_1:27017,secondaire_b_2:27017,secondaire_b_3:27017');
sh.addShard('replicaSet_c/principal_c:27017,secondaire_c_1:27017,secondaire_c_2:27017,secondaire_c_3:27017');
"

Write-Host "`n6. Vérification du statut du cluster..." -ForegroundColor Cyan
docker exec -it routeur_1 mongosh --eval "sh.status()"

Write-Host "`n=== Configuration terminée ===" -ForegroundColor Green
Write-Host "Vous pouvez maintenant vous connecter au cluster via:" -ForegroundColor Yellow
Write-Host "  mongosh mongodb://localhost:27040" -ForegroundColor White
Write-Host "  ou" -ForegroundColor Yellow
Write-Host "  mongosh mongodb://localhost:27041" -ForegroundColor White
