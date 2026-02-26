DEMO_DIR := demo
SKILLS_DIR := skills

.PHONY: help demo-sync demo-build demo-clean

help:
	@echo "alhazen-skill-examples"
	@echo "======================"
	@echo ""
	@echo "Demo commands:"
	@echo "  make demo-sync     Create symlinks from demo app into skill dashboard dirs"
	@echo "  make demo-build    Build the demo Docker image"
	@echo "  make demo-clean    Remove symlinks created by demo-sync"
	@echo ""
	@echo "Run the demo:"
	@echo "  make demo-sync && cd demo && docker compose up"

# -----------------------------------------------------------------------------
# demo-sync: wire skill dashboard components into the shared Next.js app
# -----------------------------------------------------------------------------
demo-sync:
	@echo "Syncing skill dashboard components into demo app..."

	@# jobhunt skill — use relative symlinks so they work on any machine
	@echo "  [jobhunt] components -> demo/src/components/jobhunt"
	@rm -f $(DEMO_DIR)/src/components/jobhunt
	@ln -s ../../../$(SKILLS_DIR)/demo/jobhunt/dashboard/components $(DEMO_DIR)/src/components/jobhunt

	@echo "  [jobhunt] routes -> demo/src/app/api/jobhunt"
	@rm -f $(DEMO_DIR)/src/app/api/jobhunt
	@mkdir -p $(DEMO_DIR)/src/app/api
	@ln -s ../../../../$(SKILLS_DIR)/demo/jobhunt/dashboard/routes $(DEMO_DIR)/src/app/api/jobhunt

	@echo "  [jobhunt] pages -> demo/src/app/(jobhunt)"
	@rm -f $(DEMO_DIR)/src/app/\(jobhunt\)
	@ln -s ../../../$(SKILLS_DIR)/demo/jobhunt/dashboard/pages $(DEMO_DIR)/src/app/\(jobhunt\)

	@echo "  [jobhunt] lib.ts -> demo/src/lib/jobhunt.ts"
	@rm -f $(DEMO_DIR)/src/lib/jobhunt.ts
	@ln -s ../../../$(SKILLS_DIR)/demo/jobhunt/dashboard/lib.ts $(DEMO_DIR)/src/lib/jobhunt.ts

	@echo "Done. Run: cd demo && docker compose up"

demo-clean:
	@echo "Removing demo symlinks..."
	@rm -f $(DEMO_DIR)/src/components/jobhunt
	@rm -f $(DEMO_DIR)/src/app/api/jobhunt
	@rm -f $(DEMO_DIR)/src/app/\(jobhunt\)
	@rm -f $(DEMO_DIR)/src/lib/jobhunt.ts
	@echo "Done."

demo-build:
	@echo "Building demo Docker image..."
	@cd $(DEMO_DIR) && docker build -t alhazen-skill-examples-demo .
