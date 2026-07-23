# tests/load/locustfile.py
"""
Load testing for RAG Learning Assistant
Run: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import random
import json
from faker import Faker

fake = Faker()


class AuthenticatedUser(HttpUser):
    """Simulated authenticated user"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Setup: Register and login"""
        # Register
        self.email = fake.email()
        self.username = fake.user_name()
        self.password = "TestPassword123!"
        
        register_response = self.client.post("/api/auth/register", json={
            "email": self.email,
            "username": self.username,
            "password": self.password,
            "full_name": fake.name()
        })
        
        if register_response.status_code == 200:
            # Login
            login_response = self.client.post("/api/auth/login", json={
                "email": self.email,
                "password": self.password
            })
            
            if login_response.status_code == 200:
                self.token = login_response.json()["token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                self.conversations = []
            else:
                self.token = None
        else:
            self.token = None
    
    @task(3)
    def create_conversation(self):
        """Create new conversation"""
        if not self.token:
            return
        
        response = self.client.post("/api/conversations",
            headers=self.headers,
            json={"title": f"Conversation {random.randint(1, 1000)}"},
            name="/api/conversations [CREATE]"
        )
        
        if response.status_code == 200:
            conv_id = response.json()["conversation_id"]
            self.conversations.append(conv_id)
    
    @task(5)
    def add_message(self):
        """Add message to conversation"""
        if not self.token or not self.conversations:
            return
        
        conv_id = random.choice(self.conversations)
        questions = [
            "What is data mining?",
            "Explain classification",
            "What is clustering?",
            "Describe association rules",
            "What is the Apriori algorithm?"
        ]
        
        self.client.post(
            f"/api/conversations/{conv_id}/messages",
            headers=self.headers,
            json={
                "conversation_id": conv_id,
                "role": "user",
                "content": random.choice(questions)
            },
            name="/api/conversations/{id}/messages [ADD]"
        )
    
    @task(2)
    def get_conversations(self):
        """Get user conversations"""
        if not self.token:
            return
        
        self.client.get("/api/conversations",
            headers=self.headers,
            name="/api/conversations [LIST]"
        )
    
    @task(2)
    def get_messages(self):
        """Get conversation messages"""
        if not self.token or not self.conversations:
            return
        
        conv_id = random.choice(self.conversations)
        self.client.get(
            f"/api/conversations/{conv_id}/messages",
            headers=self.headers,
            name="/api/conversations/{id}/messages [GET]"
        )
    
    @task(1)
    def get_user_info(self):
        """Get current user info"""
        if not self.token:
            return
        
        self.client.get("/api/auth/me",
            headers=self.headers,
            name="/api/auth/me"
        )
    
    @task(1)
    def get_stats(self):
        """Get user statistics"""
        if not self.token:
            return
        
        self.client.get("/api/stats",
            headers=self.headers,
            name="/api/stats"
        )
    
    @task(1)
    def search_conversations(self):
        """Search conversations"""
        if not self.token:
            return
        
        search_terms = ["data", "mining", "classification", "clustering"]
        term = random.choice(search_terms)
        
        self.client.get(f"/api/conversations/search?q={term}",
            headers=self.headers,
            name="/api/conversations/search"
        )


class RAGUser(HttpUser):
    """User asking RAG questions"""
    
    wait_time = between(2, 5)
    
    @task
    def ask_question(self):
        """Ask RAG question"""
        questions = [
            "What is data mining?",
            "Explain classification algorithms",
            "What is the difference between classification and clustering?",
            "Describe the Apriori algorithm",
            "What is association rule mining?"
        ]
        
        self.client.post("/api/question", json={
            "question": random.choice(questions),
            "session_id": None,
            "use_context": False
        }, name="/api/question")


class HealthCheckUser(HttpUser):
    """User checking health endpoints"""
    
    wait_time = between(5, 10)
    
    @task(2)
    def check_health(self):
        """Check health endpoint"""
        self.client.get("/health", name="/health")
    
    @task(1)
    def check_root(self):
        """Check root endpoint"""
        self.client.get("/", name="/")


# Event listeners for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("🚀 Load test starting...")
    print(f"Target: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("\n✅ Load test completed!")
    
    # Print statistics
    stats = environment.stats
    print(f"\nTotal requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min response time: {stats.total.min_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}")
    
    if stats.total.num_failures > 0:
        failure_rate = (stats.total.num_failures / stats.total.num_requests) * 100
        print(f"Failure rate: {failure_rate:.2f}%")


# Custom load test scenarios
class QuickTest(HttpUser):
    """Quick smoke test"""
    wait_time = between(0.5, 1)
    
    @task
    def quick_health_check(self):
        self.client.get("/health")


class StressTest(HttpUser):
    """Stress test with high load"""
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        """Login"""
        self.email = fake.email()
        register_response = self.client.post("/api/auth/register", json={
            "email": self.email,
            "username": fake.user_name(),
            "password": "TestPassword123!",
            "full_name": fake.name()
        })
        
        if register_response.status_code == 200:
            login_response = self.client.post("/api/auth/login", json={
                "email": self.email,
                "password": "TestPassword123!"
            })
            
            if login_response.status_code == 200:
                self.token = login_response.json()["token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task
    def rapid_requests(self):
        """Rapid fire requests"""
        if hasattr(self, 'token'):
            self.client.get("/api/conversations", headers=self.headers)
