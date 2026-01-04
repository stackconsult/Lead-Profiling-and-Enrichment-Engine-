"""
Enterprise integration API endpoints.
Provides REST API for managing enterprise system integrations.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.core.enterprise import (
    EnterpriseManager, 
    IntegrationConfig, 
    IntegrationType,
    EnterpriseIntegration,
    enterprise_manager
)
from backend.api.workspaces import verify_token


router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class IntegrationRequest(BaseModel):
    type: IntegrationType
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_url: Optional[str] = None
    environment: str = "production"
    custom_headers: Optional[Dict[str, str]] = None


class LeadPushRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    company: str
    phone: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None


@router.get("/integrations")
async def list_integrations(api_token: str = Depends(verify_token)) -> Dict[str, List[str]]:
    """List all configured enterprise integrations"""
    try:
        integrations = enterprise_manager.list_integrations()
        return {"integrations": integrations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list integrations: {str(e)}")


@router.post("/integrations/{integration_name}")
async def add_integration(
    integration_name: str, 
    request: IntegrationRequest,
    api_token: str = Depends(verify_token)
) -> Dict[str, str]:
    """Add a new enterprise integration"""
    try:
        config = IntegrationConfig(
            type=request.type,
            api_key=request.api_key,
            api_secret=request.api_secret,
            api_url=request.api_url,
            environment=request.environment,
            custom_headers=request.custom_headers
        )
        
        # Create integration based on type
        if request.type == IntegrationType.SALESFORCE:
            from backend.core.enterprise import SalesforceIntegration
            integration = SalesforceIntegration(config)
        elif request.type == IntegrationType.HUBSPOT:
            from backend.core.enterprise import HubSpotIntegration
            integration = HubSpotIntegration(config)
        else:
            integration = EnterpriseIntegration(config)
        
        enterprise_manager.add_integration(integration_name, integration)
        
        return {"status": "success", "message": f"Integration {integration_name} added successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add integration: {str(e)}")


@router.delete("/integrations/{integration_name}")
async def remove_integration(
    integration_name: str,
    api_token: str = Depends(verify_token)
) -> Dict[str, str]:
    """Remove an enterprise integration"""
    try:
        if integration_name in enterprise_manager.integrations:
            del enterprise_manager.integrations[integration_name]
            return {"status": "success", "message": f"Integration {integration_name} removed"}
        else:
            raise HTTPException(status_code=404, detail="Integration not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove integration: {str(e)}")


@router.get("/integrations/{integration_name}/test")
async def test_integration(
    integration_name: str,
    api_token: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Test connection to an enterprise integration"""
    try:
        integration = enterprise_manager.get_integration(integration_name)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        result = integration.test_connection()
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.get("/integrations/test-all")
async def test_all_integrations(api_token: str = Depends(verify_token)) -> Dict[str, Dict[str, Any]]:
    """Test all enterprise integrations"""
    try:
        results = enterprise_manager.test_all_connections()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tests failed: {str(e)}")


@router.get("/integrations/{integration_name}/leads")
async def sync_leads(
    integration_name: str,
    limit: int = 100,
    api_token: str = Depends(verify_token)
) -> Dict[str, List[Dict[str, Any]]]:
    """Sync leads from an enterprise integration"""
    try:
        integration = enterprise_manager.get_integration(integration_name)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        leads = integration.sync_leads(limit)
        return {"leads": leads, "count": len(leads)}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/integrations/sync-all")
async def sync_all_leads(
    limit: int = 100,
    api_token: str = Depends(verify_token)
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Sync leads from all enterprise integrations"""
    try:
        results = enterprise_manager.sync_all_leads(limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/integrations/{integration_name}/push")
async def push_lead_to_integration(
    integration_name: str,
    lead_data: LeadPushRequest,
    api_token: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Push lead data to an enterprise integration"""
    try:
        integration = enterprise_manager.get_integration(integration_name)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        lead_dict = lead_data.dict()
        result = integration.push_lead(lead_dict)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Push failed: {str(e)}")


@router.post("/integrations/push-all")
async def push_lead_to_all_integrations(
    lead_data: LeadPushRequest,
    api_token: str = Depends(verify_token)
) -> Dict[str, Dict[str, Any]]:
    """Push lead data to all enterprise integrations"""
    try:
        lead_dict = lead_data.dict()
        results = enterprise_manager.push_to_all(lead_dict)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Push failed: {str(e)}")


@router.get("/integrations/{integration_name}/account")
async def get_account_info(
    integration_name: str,
    api_token: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Get account information from an enterprise integration"""
    try:
        integration = enterprise_manager.get_integration(integration_name)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        info = integration.get_account_info()
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get account info: {str(e)}")


@router.get("/status")
async def enterprise_status(api_token: str = Depends(verify_token)) -> Dict[str, Any]:
    """Get overall enterprise integration status"""
    try:
        integrations = enterprise_manager.list_integrations()
        test_results = enterprise_manager.test_all_connections()
        
        active_count = sum(1 for result in test_results.values() if result.get("status") == "success")
        
        return {
            "total_integrations": len(integrations),
            "active_integrations": active_count,
            "integration_list": integrations,
            "connection_status": test_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
