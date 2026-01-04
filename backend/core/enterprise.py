"""
Enterprise system integrations for ProspectPulse.
Supports Salesforce, HubSpot, and other enterprise CRMs.
"""
from __future__ import annotations

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import httpx
from pydantic import BaseModel


class IntegrationType(str, Enum):
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    MICROSOFT_DYNAMICS = "microsoft_dynamics"
    SAP = "sap"
    CUSTOM = "custom"


@dataclass
class IntegrationConfig:
    type: IntegrationType
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_url: Optional[str] = None
    environment: str = "production"  # production, sandbox, development
    custom_headers: Optional[Dict[str, str]] = None


class EnterpriseIntegration:
    """Base class for enterprise integrations"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.client = httpx.Client(
            timeout=30.0,
            headers=self._get_default_headers()
        )
    
    def _get_default_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": "ProspectPulse-Enterprise/1.0",
            "Content-Type": "application/json"
        }
        
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)
            
        return headers
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to the enterprise system"""
        return {"status": "not_implemented", "message": "Connection test not implemented"}
    
    def sync_leads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Sync leads from enterprise system"""
        return []
    
    def push_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Push lead data to enterprise system"""
        return {"status": "not_implemented", "message": "Lead push not implemented"}
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account/company information"""
        return {"status": "not_implemented", "message": "Account info not implemented"}


class SalesforceIntegration(EnterpriseIntegration):
    """Salesforce CRM integration"""
    
    def _get_default_headers(self) -> Dict[str, str]:
        headers = super()._get_default_headers()
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        return headers
    
    def test_connection(self) -> Dict[str, Any]:
        try:
            if not self.config.api_url:
                return {"status": "error", "message": "Salesforce API URL required"}
            
            response = self.client.get(f"{self.config.api_url}/services/data/v53.0/sobjects/Account/describe")
            
            if response.status_code == 200:
                return {"status": "success", "message": "Salesforce connection successful"}
            else:
                return {"status": "error", "message": f"Salesforce API error: {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {str(e)}"}
    
    def sync_leads(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            query = f"SELECT Id, FirstName, LastName, Email, Company, Phone, LeadSource FROM Lead LIMIT {limit}"
            response = self.client.get(f"{self.config.api_url}/services/data/v53.0/query", params={"q": query})
            
            if response.status_code == 200:
                data = response.json()
                return data.get("records", [])
            else:
                return []
                
        except Exception as e:
            print(f"Salesforce sync error: {e}")
            return []
    
    def push_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Map ProspectPulse data to Salesforce fields
            sf_lead = {
                "FirstName": lead_data.get("first_name", ""),
                "LastName": lead_data.get("last_name", ""),
                "Email": lead_data.get("email", ""),
                "Company": lead_data.get("company", ""),
                "Phone": lead_data.get("phone", ""),
                "LeadSource": "ProspectPulse",
                "Description": json.dumps(lead_data.get("analysis", {}))
            }
            
            response = self.client.post(f"{self.config.api_url}/services/data/v53.0/sobjects/Lead", json=sf_lead)
            
            if response.status_code == 201:
                result = response.json()
                return {"status": "success", "salesforce_id": result.get("id")}
            else:
                return {"status": "error", "message": f"Salesforce API error: {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "message": f"Lead push failed: {str(e)}"}


class HubSpotIntegration(EnterpriseIntegration):
    """HubSpot CRM integration"""
    
    def _get_default_headers(self) -> Dict[str, str]:
        headers = super()._get_default_headers()
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        return headers
    
    def test_connection(self) -> Dict[str, Any]:
        try:
            response = self.client.get("https://api.hubapi.com/crm/v3/objects/contacts?limit=1")
            
            if response.status_code == 200:
                return {"status": "success", "message": "HubSpot connection successful"}
            else:
                return {"status": "error", "message": f"HubSpot API error: {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {str(e)}"}
    
    def sync_leads(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            response = self.client.get("https://api.hubapi.com/crm/v3/objects/contacts", params={"limit": limit})
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                return []
                
        except Exception as e:
            print(f"HubSpot sync error: {e}")
            return []
    
    def push_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Map ProspectPulse data to HubSpot properties
            hs_contact = {
                "properties": {
                    "firstname": lead_data.get("first_name", ""),
                    "lastname": lead_data.get("last_name", ""),
                    "email": lead_data.get("email", ""),
                    "company": lead_data.get("company", ""),
                    "phone": lead_data.get("phone", ""),
                    "lifecyclestage": "lead",
                    "prospectpulse_analysis": json.dumps(lead_data.get("analysis", {}))
                }
            }
            
            response = self.client.post("https://api.hubapi.com/crm/v3/objects/contacts", json=hs_contact)
            
            if response.status_code == 201:
                result = response.json()
                return {"status": "success", "hubspot_id": result.get("id")}
            else:
                return {"status": "error", "message": f"HubSpot API error: {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "message": f"Lead push failed: {str(e)}"}


class EnterpriseManager:
    """Manages multiple enterprise integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, EnterpriseIntegration] = {}
        self._load_integrations()
    
    def _load_integrations(self):
        """Load integrations from environment variables"""
        # Salesforce
        if os.getenv("SALESFORCE_API_KEY") and os.getenv("SALESFORCE_API_URL"):
            config = IntegrationConfig(
                type=IntegrationType.SALESFORCE,
                api_key=os.getenv("SALESFORCE_API_KEY"),
                api_url=os.getenv("SALESFORCE_API_URL"),
                environment=os.getenv("SALESFORCE_ENV", "production")
            )
            self.integrations["salesforce"] = SalesforceIntegration(config)
        
        # HubSpot
        if os.getenv("HUBSPOT_API_KEY"):
            config = IntegrationConfig(
                type=IntegrationType.HUBSPOT,
                api_key=os.getenv("HUBSPOT_API_KEY"),
                environment=os.getenv("HUBSPOT_ENV", "production")
            )
            self.integrations["hubspot"] = HubSpotIntegration(config)
    
    def add_integration(self, name: str, integration: EnterpriseIntegration):
        """Add a new integration"""
        self.integrations[name] = integration
    
    def get_integration(self, name: str) -> Optional[EnterpriseIntegration]:
        """Get an integration by name"""
        return self.integrations.get(name)
    
    def list_integrations(self) -> List[str]:
        """List all available integrations"""
        return list(self.integrations.keys())
    
    def test_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """Test all integrations"""
        results = {}
        for name, integration in self.integrations.items():
            results[name] = integration.test_connection()
        return results
    
    def sync_all_leads(self, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """Sync leads from all integrations"""
        results = {}
        for name, integration in self.integrations.items():
            results[name] = integration.sync_leads(limit)
        return results
    
    def push_to_all(self, lead_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Push lead to all integrations"""
        results = {}
        for name, integration in self.integrations.items():
            results[name] = integration.push_lead(lead_data)
        return results


# Global enterprise manager instance
enterprise_manager = EnterpriseManager()
