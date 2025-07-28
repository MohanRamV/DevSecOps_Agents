import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";



export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [issues, setIssues] = useState([]);
  const [tab, setTab] = useState("pipeline");
  const [loading, setLoading] = useState(false);

  const fetchHealth = async () => {
    const res = await fetch("/health");
    const data = await res.json();
    setHealth(data);
  };

  const fetchIssues = async () => {
    const res = await fetch("/issues");
    const data = await res.json();
    setIssues(data.issues);
  };

  const trigger = async (endpoint) => {
    setLoading(true);
    await fetch(endpoint, { method: "POST" });
    setTimeout(() => {
      fetchHealth();
      fetchIssues();
      setLoading(false);
    }, 2000);
  };

  useEffect(() => {
    fetchHealth();
    fetchIssues();
  }, []);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">🛡️ DevSecOps AI Monitoring Dashboard</h1>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="pipeline">Pipeline Agent</TabsTrigger>
          <TabsTrigger value="deployment">Deployment Agent</TabsTrigger>
          <TabsTrigger value="notification">Notification Agent</TabsTrigger>
        </TabsList>

        <TabsContent value="pipeline">
          <Card>
            <CardContent className="p-4 space-y-3">
              <div className="flex justify-between">
                <h2 className="text-lg font-semibold">Pipeline Monitor</h2>
                <Button onClick={() => trigger("/monitor/pipeline")} disabled={loading}>
                  {loading ? "Running..." : "Run Now"}
                </Button>
              </div>
              <p>Status: <Badge>{health?.agents?.pipeline_monitor?.status || "loading"}</Badge></p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="deployment">
          <Card>
            <CardContent className="p-4 space-y-3">
              <div className="flex justify-between">
                <h2 className="text-lg font-semibold">Deployment Monitor</h2>
                <Button onClick={() => trigger("/monitor/deployment")} disabled={loading}>
                  {loading ? "Running..." : "Run Now"}
                </Button>
              </div>
              <p>Status: <Badge>{health?.agents?.deployment_monitor?.status || "loading"}</Badge></p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notification">
          <Card>
            <CardContent className="p-4 space-y-3">
              <div className="flex justify-between">
                <h2 className="text-lg font-semibold">Notification Agent</h2>
                <Button onClick={() => trigger("/notify")} disabled={loading}>
                  {loading ? "Sending..." : "Send Now"}
                </Button>
              </div>
              <p>Status: <Badge>{health?.agents?.notification?.status || "loading"}</Badge></p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="pt-6">
        <h2 className="text-xl font-bold mb-4">⚠️ Issues</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {issues.map((issue) => (
            <Card key={issue.id}>
              <CardContent className="p-4 space-y-2">
                <div className="flex justify-between">
                  <h3 className="font-semibold">{issue.title}</h3>
                  <Badge>{issue.severity}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{issue.description}</p>
                {issue.suggested_fixes?.immediate_fixes && (
                  <div className="mt-2">
                    <h4 className="text-sm font-semibold">Suggested Fixes:</h4>
                    <ul className="text-xs list-disc ml-4">
                      {issue.suggested_fixes.immediate_fixes.map((fix, i) => (
                        <li key={i}>{fix.title}: {fix.description}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
