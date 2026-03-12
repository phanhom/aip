"""Tests for AIP status models."""

from aip import AgentStatus, GroupStatus, RecursiveStatusNode, StatusEndpoints, StatusScope


class TestAgentStatus:
    def test_minimal(self):
        s = AgentStatus(agent_id="backend", role="engineer")
        assert s.agent_id == "backend"
        assert s.ok is True
        assert s.pending_tasks == 0
        assert s.capabilities == []
        assert s.supported_versions == ["1.0"]

    def test_with_endpoints(self):
        s = AgentStatus(
            agent_id="backend",
            role="engineer",
            base_url="https://backend.example.com",
            endpoints=StatusEndpoints(
                aip="https://backend.example.com/aip",
                status="https://backend.example.com/status",
            ),
        )
        assert s.endpoints is not None
        assert s.endpoints.aip == "https://backend.example.com/aip"


class TestRecursiveStatusNode:
    def test_tree(self):
        leaf = RecursiveStatusNode(
            self=AgentStatus(agent_id="worker", role="dev"),
            subordinates=[],
        )
        root = RecursiveStatusNode(
            self=AgentStatus(agent_id="coordinator", role="lead"),
            subordinates=[leaf],
        )
        assert len(root.subordinates) == 1
        assert root.subordinates[0].self.agent_id == "worker"


class TestGroupStatus:
    def test_flat(self):
        g = GroupStatus(
            root_agent_id="coordinator",
            topology={"coordinator": ["a", "b"]},
            agents=[
                AgentStatus(agent_id="coordinator", role="lead"),
                AgentStatus(agent_id="a", role="dev"),
                AgentStatus(agent_id="b", role="qa"),
            ],
        )
        assert g.ok is True
        assert len(g.agents) == 3
        assert g.topology["coordinator"] == ["a", "b"]


class TestStatusScope:
    def test_values(self):
        assert StatusScope.self_scope == "self"
        assert StatusScope.subtree == "subtree"
        assert StatusScope.group == "group"
