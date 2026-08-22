# One-click entry points for the test workflow.
#
# The canonical acceptance command is:
#   docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile test run test
# `make test` runs the equivalent: generate secrets, build the dev image, run the suite.

COMPOSE_BASE  := docker-compose.yml
COMPOSE_DEV   := docker-compose.dev.yml
COMPOSE_BUILD := docker-compose.build.yml
COMPOSE_TEST  := docker compose -f $(COMPOSE_BASE) -f $(COMPOSE_DEV)

.PHONY: secrets build test

secrets: ## Generate local secrets under secrets/ (idempotent)
	./scripts/gen-secrets.sh

build: ## Build the postgres and bndsphere-backend:dev images used by the test service
	docker compose -f $(COMPOSE_BASE) -f $(COMPOSE_BUILD) build postgres backend-dev

test: secrets build ## Generate secrets, build images, run the pytest suite
	$(COMPOSE_TEST) --profile test run test
