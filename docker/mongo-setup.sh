#!/bin/bash

docker compose up --wait

sleep 10

mongosh --host principal_a:27017 <<EOF
  var cfg = {
    "_id": "principal_a",
    "version": 1,
    "members": [
      {
        "_id": 0,
        "host": "secondaire_a_1:27017",
        "priority": 2
      },
      {
        "_id": 1,
        "host": "secondaire_a_2:27017",
        "priority": 1
      },
      {
        "_id": 2,
        "host": "secondaire_a_3:27017",
        "priority": 0
      }
    ]
  };
  rs.initiate(cfg);
EOF

mongosh --host principal_b:27017 <<EOF
  var cfg = {
    "_id": "principal_b",
    "version": 1,
    "members": [
      {
        "_id": 0,
        "host": "secondaire_b_1:27017",
        "priority": 2
      },
      {
        "_id": 1,
        "host": "secondaire_b_2:27017",
        "priority": 1
      },
      {
        "_id": 2,
        "host": "secondaire_b_3:27017",
        "priority": 0
      }
    ]
  };
  rs.initiate(cfg);
EOF

mongosh --host principal_c:27017 <<EOF
  var cfg = {
    "_id": "principal_c",
    "version": 1,
    "members": [
      {
        "_id": 0,
        "host": "secondaire_c_1:27017",
        "priority": 2
      },
      {
        "_id": 1,
        "host": "secondaire_c_2:27017",
        "priority": 1
      },
      {
        "_id": 2,
        "host": "secondaire_c_3:27017",
        "priority": 0
      }
    ]
  };
  rs.initiate(cfg);
EOF