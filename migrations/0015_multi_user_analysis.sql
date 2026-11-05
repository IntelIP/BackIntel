ALTER TABLE backintel.analysis_principals ADD COLUMN IF NOT EXISTS administrator boolean NOT NULL DEFAULT false;
ALTER TABLE backintel.analysis_principals ADD COLUMN IF NOT EXISTS budget_usd numeric NOT NULL DEFAULT 0 CHECK (budget_usd >= 0);

CREATE TABLE IF NOT EXISTS backintel.analysis_goal_access (
    goal_id text NOT NULL REFERENCES backintel.analysis_goals(id),
    principal_id text NOT NULL REFERENCES backintel.analysis_principals(id),
    permission text NOT NULL CHECK (permission IN ('read','run','manage')),
    PRIMARY KEY (goal_id, principal_id)
);
CREATE INDEX IF NOT EXISTS analysis_goal_access_principal ON backintel.analysis_goal_access(principal_id,goal_id);
