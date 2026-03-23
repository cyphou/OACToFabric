// ============================================================================
// OAC-to-Fabric Migration Infrastructure — Azure Bicep
// ============================================================================
// Deploys:
//   - Resource Group (implicit)
//   - Azure OpenAI Service
//   - Application Insights (telemetry)
//   - Key Vault (secrets management)
//   - Fabric Workspace (reference only — provisioned via Fabric portal/API)
//
// Usage:
//   az deployment sub create \
//     --location eastus2 \
//     --template-file infra/main.bicep \
//     --parameters environment=dev projectName=oac-migration

targetScope = 'subscription'

// ----- Parameters -----

@description('Environment name (dev, test, prod)')
@allowed(['dev', 'test', 'prod'])
param environment string = 'dev'

@description('Project name prefix for all resources')
param projectName string = 'oac-migration'

@description('Azure region for resources')
param location string = 'eastus2'

@description('Tags applied to all resources')
param tags object = {
  project: 'OAC-to-Fabric-Migration'
  environment: environment
  managedBy: 'bicep'
}

// ----- Variables -----

var resourceGroupName = 'rg-${projectName}-${environment}'
var openAIName = 'oai-${projectName}-${environment}'
var appInsightsName = 'appi-${projectName}-${environment}'
var logAnalyticsName = 'law-${projectName}-${environment}'
var keyVaultName = 'kv-${take(projectName, 10)}-${environment}'

// ----- Resource Group -----

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ----- Module: Core Infrastructure -----

module coreInfra 'modules/core.bicep' = {
  name: 'core-${environment}'
  scope: rg
  params: {
    location: location
    tags: tags
    openAIName: openAIName
    appInsightsName: appInsightsName
    logAnalyticsName: logAnalyticsName
    keyVaultName: keyVaultName
    environment: environment
  }
}

// ----- Outputs -----

output resourceGroupName string = rg.name
output openAIEndpoint string = coreInfra.outputs.openAIEndpoint
output appInsightsConnectionString string = coreInfra.outputs.appInsightsConnectionString
output keyVaultUri string = coreInfra.outputs.keyVaultUri
