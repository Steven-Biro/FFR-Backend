set -x
mongo ffrdb --verbose --eval "
db.createUser({user: \"ffrbot\", pwd: \"password\", roles: [{role: \"readWrite\", db: \"ffrdb\"}]});

db.createCollection(\"races\", {
    validator: {
        \$jsonSchema: {
            bsonType: \"array\",
            items: $(<./schemas/race.json)
        }
    }
})"
