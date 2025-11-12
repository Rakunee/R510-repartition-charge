#!/usr/bin/env bash
set -euo pipefail

# Script de vérification du cluster sharded + replica sets
# Usage: bash scripts/check_cluster.sh
# Nécessite: docker (et que les conteneurs soient démarrés)

MONGOS_CONTAINER=${MONGOS_CONTAINER:-routeur_1}
ALT_MONGOS_CONTAINER=${ALT_MONGOS_CONTAINER:-routeur_2}
CONFIG_CONTAINER=${CONFIG_CONTAINER:-config_server_1}
SHARD_CONTAINERS=(principal_a principal_b principal_c)
SECONDARY_TEST_CONTAINER=${SECONDARY_TEST_CONTAINER:-secondaire_a_1}

function run_mongosh_container() {
  local container="$1"
  shift
  docker exec -i "$container" mongosh --quiet --eval "$*"
}

echo "============================================================"
echo " Vérification du cluster MongoDB sharded (via containers Docker)"
echo "============================================================"

echo -e "\n--- sh.status() via $MONGOS_CONTAINER ---"
run_mongosh_container "$MONGOS_CONTAINER" "sh.status()"

echo -e "\n--- sh.status() via $ALT_MONGOS_CONTAINER (si disponible) ---"
if docker ps --format '{{.Names}}' | grep -q "^$ALT_MONGOS_CONTAINER$"; then
  run_mongosh_container "$ALT_MONGOS_CONTAINER" "sh.status()"
else
  echo "Container $ALT_MONGOS_CONTAINER non trouvé, skip."
fi

echo -e "\n--- Balancer state (via $MONGOS_CONTAINER) ---"
run_mongosh_container "$MONGOS_CONTAINER" "print('sh.getBalancerState() =', sh.getBalancerState()); print('sh.isBalancerRunning() =', sh.isBalancerRunning());"

echo -e "\n--- Distribution des chunks par shard (depuis config.chunks) ---"
run_mongosh_container "$MONGOS_CONTAINER" "db.getSiblingDB('config').chunks.aggregate([{
  \$group:{_id:'\$shard',count:{\$sum:1}}
}]).forEach(printjson)"

echo -e "\n--- Statut du replica set des config servers (sur $CONFIG_CONTAINER) ---"
if docker ps --format '{{.Names}}' | grep -q "^$CONFIG_CONTAINER$"; then
  docker exec -i "$CONFIG_CONTAINER" mongosh --quiet --eval "rs.status().members.forEach(m=>printjson({name:m.name,state:m.stateStr,health:m.health,lastHeartbeat:m.lastHeartbeat}))"
else
  echo "Container $CONFIG_CONTAINER non trouvé, skip."
fi

for s in "${SHARD_CONTAINERS[@]}"; do
  echo -e "\n--- rs.status() sur le replica set du shard container: $s ---"
  if docker ps --format '{{.Names}}' | grep -q "^$s$"; then
    docker exec -i "$s" mongosh --quiet --eval "rs.status().members.forEach(m=>printjson({name:m.name,state:m.stateStr,uptime:m.uptime,optime:m.optimeDate}))"
  else
    echo "Container $s non trouvé, skip."
  fi
done

echo -e "\n--- Test pratique de réplication ---"
echo "Insertion via mongos ($MONGOS_CONTAINER) dans la base 'tp', collection 'books'"
run_mongosh_container "$MONGOS_CONTAINER" "db = db.getSiblingDB('tp'); db.books.insertOne({__testReplication:true,ts:new Date()}); print('insert done')"

echo -e "Lecture sur un secondaire (container $SECONDARY_TEST_CONTAINER) avec readPref secondaryPreferred"
if docker ps --format '{{.Names}}' | grep -q "^$SECONDARY_TEST_CONTAINER$"; then
  docker exec -i "$SECONDARY_TEST_CONTAINER" mongosh --quiet --eval "db.getMongo().setReadPref('secondaryPreferred'); db.getSiblingDB('tp').books.find({__testReplication:true}).limit(1).forEach(printjson)"
else
  echo "Container $SECONDARY_TEST_CONTAINER non trouvé, skip lecture sur secondaire."
fi

echo -e "\n--- Quelques logs récents pour debug (principal_a & config_server_1) ---"
docker logs principal_a --tail 50 || true
docker logs config_server_1 --tail 50 || true

echo -e "\nFini. Interprétez les sorties: cherchez 'PRIMARY' et 'SECONDARY' dans rs.status(), et vérifiez que sh.status() montre 3 shards et des chunks répartis."
echo "Si vous voulez exécuter ce script depuis PowerShell/Windows: utilisez Git Bash, WSL ou 'bash' si installé, ex: 'bash scripts/check_cluster.sh'"
