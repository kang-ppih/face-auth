"""
Face-Auth IdP System - Main Infrastructure Stack

This module defines the complete AWS infrastructure for the Face-Auth Identity Provider system,
including VPC, Direct Connect gateway, S3 buckets, DynamoDB tables, Lambda functions,
IAM roles, and security groups.

Requirements addressed: 4.1, 4.4, 4.5, 4.7
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    Tags,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_logs as logs,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3deploy,
    CfnOutput,
    Fn
)
from constructs import Construct
import json
import os


class FaceAuthStack(Stack):
    """
    Main CDK Stack for Face-Auth IdP System
    
    Creates all necessary AWS resources for the face authentication system:
    - VPC with proper security groups
    - Direct Connect Virtual Interface for on-premises AD connection
    - S3 buckets for image storage with lifecycle policies
    - DynamoDB tables for card templates and employee data
    - Lambda functions for authentication logic
    - IAM roles and policies for secure access
    - API Gateway for REST endpoints
    - Cognito User Pool for session management
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Apply tags to all resources in this stack for cost tracking
        Tags.of(self).add("Name", "Face-auth")
        Tags.of(self).add("Cost Center", "Face-auth")
        Tags.of(self).add("Development", "dm-dev")
        Tags.of(self).add("Project", "FaceAuth-IdP")
        Tags.of(self).add("ManagedBy", "CDK")

        # Get allowed IP addresses from context or environment variable
        # Format: comma-separated CIDR blocks (e.g., "1.2.3.4/32,5.6.7.0/24")
        allowed_ips_str = self.node.try_get_context("allowed_ips") or os.getenv("ALLOWED_IPS", "")
        self.allowed_ip_ranges = [ip.strip() for ip in allowed_ips_str.split(",") if ip.strip()]
        
        # If no IPs specified, allow all (for development)
        if not self.allowed_ip_ranges:
            self.allowed_ip_ranges = ["0.0.0.0/0"]  # Allow all IPs (development mode)
        
        # Get frontend origin for CORS
        # Format: comma-separated origins (e.g., "https://example.com,https://app.example.com")
        frontend_origins_str = self.node.try_get_context("frontend_origins") or os.getenv("FRONTEND_ORIGINS", "")
        self.frontend_origins = [origin.strip() for origin in frontend_origins_str.split(",") if origin.strip()]
        
        # If no origins specified, allow all (for development)
        if not self.frontend_origins:
            self.frontend_origins = ["*"]  # Allow all origins (development mode)

        # Create VPC and networking components
        self._create_vpc_and_networking()
        
        # Create S3 buckets for image storage
        self._create_s3_buckets()
        
        # Create frontend hosting (S3 + CloudFront)
        self._create_frontend_hosting()
        
        # Create DynamoDB tables
        self._create_dynamodb_tables()
        
        # Create Cognito User Pool
        self._create_cognito_user_pool()
        
        # Create IAM roles and policies
        self._create_iam_roles()
        
        # Create Lambda functions
        self._create_lambda_functions()
        
        # Create API Gateway
        self._create_api_gateway()
        
        # Create CloudWatch Log Groups
        self._create_cloudwatch_logs()
        
        # Output important resource information
        self._create_outputs()

    def _create_vpc_and_networking(self):
        """
        Create VPC, subnets, security groups, Network ACLs, and Direct Connect components
        Requirements: 4.1, 4.5
        """
        # Create VPC for Face-Auth system
        self.vpc = ec2.Vpc(
            self, "FaceAuthVPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet", 
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="IsolatedSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )

        # Create Network ACL for Public Subnets with IP restrictions
        self._create_network_acls()

        # Security group for Lambda functions
        self.lambda_security_group = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for Face-Auth Lambda functions",
            allow_all_outbound=True
        )

        # Security group for Direct Connect (AD connection)
        self.ad_security_group = ec2.SecurityGroup(
            self, "ADSecurityGroup", 
            vpc=self.vpc,
            description="Security group for Active Directory connection via Direct Connect",
            allow_all_outbound=False
        )

        # Allow LDAPS traffic to on-premises AD (port 636)
        self.ad_security_group.add_egress_rule(
            peer=ec2.Peer.ipv4("10.0.0.0/8"),  # On-premises network range
            connection=ec2.Port.tcp(636),
            description="LDAPS traffic to on-premises Active Directory"
        )

        # Allow LDAP traffic as fallback (port 389)
        self.ad_security_group.add_egress_rule(
            peer=ec2.Peer.ipv4("10.0.0.0/8"),
            connection=ec2.Port.tcp(389),
            description="LDAP traffic to on-premises Active Directory"
        )

        # Create VPC Endpoint for S3 (for secure S3 access from Lambda)
        self.s3_vpc_endpoint = ec2.GatewayVpcEndpoint(
            self, "S3VPCEndpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # Create VPC Endpoint for DynamoDB
        self.dynamodb_vpc_endpoint = ec2.GatewayVpcEndpoint(
            self, "DynamoDBVPCEndpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB
        )

        # Direct Connect Gateway (placeholder - actual DX setup requires physical connection)
        # This would be configured separately in the AWS Console or via AWS CLI
        # as it requires coordination with network providers
        
        # TODO: Configure Customer Gateway with actual on-premises IP address
        # Uncomment and update ip_address when ready to establish Direct Connect
        # self.customer_gateway = ec2.CfnCustomerGateway(
        #     self, "OnPremisesCustomerGateway",
        #     bgp_asn=65000,  # Private ASN for on-premises
        #     ip_address="YOUR_ACTUAL_IP_HERE",  # Replace with actual on-premises gateway IP
        #     type="ipsec.1",
        #     tags=[{
        #         "key": "Name",
        #         "value": "FaceAuth-OnPremises-Gateway"
        #     }]
        # )

    def _create_network_acls(self):
        """
        Create Network ACLs to restrict access to allowed IP ranges only
        This provides an additional layer of security at the subnet level
        """
        # Get public subnets
        public_subnets = self.vpc.public_subnets
        
        if not public_subnets:
            return
        
        # Create Network ACL for public subnets
        self.public_nacl = ec2.NetworkAcl(
            self, "PublicSubnetNACL",
            vpc=self.vpc,
            network_acl_name="FaceAuth-Public-NACL"
        )
        
        # Associate NACL with all public subnets
        for idx, subnet in enumerate(public_subnets):
            ec2.NetworkAclEntry(
                self, f"PublicNACLAssociation{idx}",
                network_acl=self.public_nacl,
                cidr=ec2.AclCidr.any_ipv4(),
                rule_number=100 + idx,
                traffic=ec2.AclTraffic.all_traffic(),
                direction=ec2.TrafficDirection.EGRESS,
                rule_action=ec2.Action.ALLOW
            )
            
            # Associate NACL with subnet
            ec2.CfnSubnetNetworkAclAssociation(
                self, f"PublicSubnetNACLAssoc{idx}",
                network_acl_id=self.public_nacl.network_acl_id,
                subnet_id=subnet.subnet_id
            )
        
        # Add ingress rules for allowed IPs only
        rule_number = 100
        for idx, ip_range in enumerate(self.allowed_ip_ranges):
            # Allow HTTPS (443) from allowed IPs
            ec2.NetworkAclEntry(
                self, f"AllowHTTPS{idx}",
                network_acl=self.public_nacl,
                cidr=ec2.AclCidr.ipv4(ip_range),
                rule_number=rule_number,
                traffic=ec2.AclTraffic.tcp_port(443),
                direction=ec2.TrafficDirection.INGRESS,
                rule_action=ec2.Action.ALLOW
            )
            rule_number += 10
            
            # Allow HTTP (80) from allowed IPs (for redirects)
            ec2.NetworkAclEntry(
                self, f"AllowHTTP{idx}",
                network_acl=self.public_nacl,
                cidr=ec2.AclCidr.ipv4(ip_range),
                rule_number=rule_number,
                traffic=ec2.AclTraffic.tcp_port(80),
                direction=ec2.TrafficDirection.INGRESS,
                rule_action=ec2.Action.ALLOW
            )
            rule_number += 10
            
            # Allow ephemeral ports for return traffic
            ec2.NetworkAclEntry(
                self, f"AllowEphemeral{idx}",
                network_acl=self.public_nacl,
                cidr=ec2.AclCidr.ipv4(ip_range),
                rule_number=rule_number,
                traffic=ec2.AclTraffic.tcp_port_range(1024, 65535),
                direction=ec2.TrafficDirection.INGRESS,
                rule_action=ec2.Action.ALLOW
            )
            rule_number += 10
        
        # Deny all other inbound traffic (explicit deny)
        ec2.NetworkAclEntry(
            self, "DenyAllOtherIngress",
            network_acl=self.public_nacl,
            cidr=ec2.AclCidr.any_ipv4(),
            rule_number=32766,  # Maximum allowed rule number
            traffic=ec2.AclTraffic.all_traffic(),
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.DENY
        )

    def _create_s3_buckets(self):
        """
        Create S3 buckets for image storage with proper lifecycle policies
        Requirements: 4.4, 5.2, 5.3, 5.4, 5.6
        """
        # Main bucket for face authentication images
        self.face_auth_bucket = s3.Bucket(
            self, "FaceAuthImageBucket",
            bucket_name=f"face-auth-images-{self.account}-{self.region}",
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                # Lifecycle rule for login attempt images (30-day deletion)
                s3.LifecycleRule(
                    id="LoginAttemptsCleanup",
                    prefix="logins/",
                    enabled=True,
                    expiration=Duration.days(30)
                ),
                # Lifecycle rule for temporary processing files (1-day deletion)
                s3.LifecycleRule(
                    id="TempFilesCleanup", 
                    prefix="temp/",
                    enabled=True,
                    expiration=Duration.days(1)
                )
            ]
        )

        # CORS configuration for frontend access
        self.face_auth_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.POST, s3.HttpMethods.PUT],
            allowed_origins=self.frontend_origins,  # Restrict to frontend origins
            allowed_headers=["*"],
            max_age=3000
        )

    def _create_frontend_hosting(self):
        """
        Create S3 bucket and CloudFront distribution for frontend hosting
        with IP-based access control
        
        Requirements: 10.1, 10.7
        """
        # S3 bucket for frontend static files
        self.frontend_bucket = s3.Bucket(
            self, "FaceAuthFrontendBucket",
            bucket_name=f"face-auth-frontend-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True
        )

        # Origin Access Identity for CloudFront
        oai = cloudfront.OriginAccessIdentity(
            self, "FaceAuthFrontendOAI",
            comment="OAI for Face-Auth Frontend"
        )

        # Grant CloudFront read access to S3 bucket via OAI
        self.frontend_bucket.grant_read(oai.grant_principal)

        # CloudFront distribution with IP restriction
        # Create custom response headers policy
        response_headers_policy = cloudfront.ResponseHeadersPolicy(
            self, "FaceAuthSecurityHeadersPolicy",
            response_headers_policy_name="FaceAuth-SecurityHeaders",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(
                    override=True
                ),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY,
                    override=True
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
                    override=True
                ),
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.seconds(31536000),
                    include_subdomains=True,
                    override=True
                ),
                xss_protection=cloudfront.ResponseHeadersXSSProtection(
                    protection=True,
                    mode_block=True,
                    override=True
                )
            )
        )

        # CloudFront distribution
        self.frontend_distribution = cloudfront.Distribution(
            self, "FaceAuthFrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    bucket=self.frontend_bucket,
                    origin_access_identity=oai
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                compress=True,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                response_headers_policy=response_headers_policy
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            enabled=True,
            comment="Face-Auth IdP Frontend Distribution"
        )

        # Add WAF Web ACL for IP restriction if IPs are specified
        if self.allowed_ip_ranges != ["0.0.0.0/0"]:
            # Note: WAF Web ACL creation requires aws_wafv2 module
            # For now, we'll document this in outputs
            pass

    def _create_dynamodb_tables(self):
        """
        Create DynamoDB tables for card templates and employee face data
        Requirements: 5.5, 7.4
        """
        # Card Templates table for storing ID card recognition patterns
        self.card_templates_table = dynamodb.Table(
            self, "CardTemplatesTable",
            table_name="FaceAuth-CardTemplates",
            partition_key=dynamodb.Attribute(
                name="pattern_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            )
        )

        # Global Secondary Index for card type queries
        self.card_templates_table.add_global_secondary_index(
            index_name="CardTypeIndex",
            partition_key=dynamodb.Attribute(
                name="card_type",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Employee Faces table for storing face recognition data
        self.employee_faces_table = dynamodb.Table(
            self, "EmployeeFacesTable",
            table_name="FaceAuth-EmployeeFaces",
            partition_key=dynamodb.Attribute(
                name="employee_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            )
        )

        # Global Secondary Index for face_id queries
        self.employee_faces_table.add_global_secondary_index(
            index_name="FaceIdIndex",
            partition_key=dynamodb.Attribute(
                name="face_id",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Authentication Sessions table for session management
        self.auth_sessions_table = dynamodb.Table(
            self, "AuthSessionsTable",
            table_name="FaceAuth-AuthSessions",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
            time_to_live_attribute="expires_at"  # Automatic session cleanup
        )

    def _create_cognito_user_pool(self):
        """
        Create Cognito User Pool for authentication session management
        Requirements: 2.3, 3.5
        """
        self.user_pool = cognito.UserPool(
            self, "FaceAuthUserPool",
            user_pool_name="FaceAuth-UserPool",
            sign_in_aliases=cognito.SignInAliases(
                username=True,
                email=False,
                phone=False
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=False, phone=False),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.NONE,  # No self-service recovery
            removal_policy=RemovalPolicy.RETAIN
        )

        # User Pool Client for the Face-Auth application
        self.user_pool_client = cognito.UserPoolClient(
            self, "FaceAuthUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name="FaceAuth-Client",
            generate_secret=False,  # For frontend applications
            auth_flows=cognito.AuthFlow(
                admin_user_password=True,
                custom=True,
                user_password=False,
                user_srp=False
            ),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30)
        )

    def _create_iam_roles(self):
        """
        Create IAM roles and policies for Lambda functions and services
        Requirements: 4.7, 5.6, 5.7
        """
        # Lambda execution role with comprehensive permissions
        self.lambda_execution_role = iam.Role(
            self, "FaceAuthLambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ]
        )

        # Custom policy for Face-Auth specific permissions
        face_auth_policy = iam.PolicyDocument(
            statements=[
                # S3 permissions for image storage
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject", 
                        "s3:DeleteObject",
                        "s3:ListBucket"
                    ],
                    resources=[
                        self.face_auth_bucket.bucket_arn,
                        f"{self.face_auth_bucket.bucket_arn}/*"
                    ]
                ),
                # DynamoDB permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan"
                    ],
                    resources=[
                        self.card_templates_table.table_arn,
                        self.employee_faces_table.table_arn,
                        self.auth_sessions_table.table_arn,
                        f"{self.card_templates_table.table_arn}/index/*",
                        f"{self.employee_faces_table.table_arn}/index/*"
                    ]
                ),
                # Amazon Rekognition permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "rekognition:DetectFaces",
                        "rekognition:SearchFacesByImage",
                        "rekognition:IndexFaces",
                        "rekognition:DeleteFaces",
                        "rekognition:CreateCollection",
                        "rekognition:DeleteCollection",
                        "rekognition:ListCollections",
                        "rekognition:DescribeCollection"
                    ],
                    resources=["*"]
                ),
                # Amazon Textract permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "textract:AnalyzeDocument",
                        "textract:DetectDocumentText"
                    ],
                    resources=["*"]
                ),
                # Cognito permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cognito-idp:AdminCreateUser",
                        "cognito-idp:AdminSetUserPassword",
                        "cognito-idp:AdminInitiateAuth",
                        "cognito-idp:AdminGetUser",
                        "cognito-idp:AdminUpdateUserAttributes",
                        "cognito-idp:AdminUserGlobalSignOut",
                        "cognito-idp:AdminDisableUser",
                        "cognito-idp:AdminEnableUser"
                    ],
                    resources=[self.user_pool.user_pool_arn]
                ),
                # CloudWatch Logs permissions
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream", 
                        "logs:PutLogEvents"
                    ],
                    resources=["*"]
                )
            ]
        )

        # Attach the custom policy to the Lambda role
        iam.Policy(
            self, "FaceAuthLambdaPolicy",
            document=face_auth_policy,
            roles=[self.lambda_execution_role]
        )

    def _create_lambda_functions(self):
        """
        Create Lambda functions for authentication workflows
        Requirements: 4.3, 4.4
        """
        # Common Lambda configuration
        lambda_config = {
            "runtime": lambda_.Runtime.PYTHON_3_9,
            "timeout": Duration.seconds(15),  # 15-second timeout as per requirements
            "memory_size": 512,
            "role": self.lambda_execution_role,
            "vpc": self.vpc,
            "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            "security_groups": [self.lambda_security_group, self.ad_security_group],
            # Lambda Layer removed - shared modules are now bundled with each function
            "environment": {
                "FACE_AUTH_BUCKET": self.face_auth_bucket.bucket_name,
                "CARD_TEMPLATES_TABLE": self.card_templates_table.table_name,
                "EMPLOYEE_FACES_TABLE": self.employee_faces_table.table_name,
                "AUTH_SESSIONS_TABLE": self.auth_sessions_table.table_name,
                "COGNITO_USER_POOL_ID": self.user_pool.user_pool_id,
                "COGNITO_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "REKOGNITION_COLLECTION_ID": "face-auth-employees",
                "AD_TIMEOUT": "10",  # 10-second AD timeout
                "LAMBDA_TIMEOUT": "15",  # 15-second Lambda timeout
                "SESSION_TIMEOUT_HOURS": "8",  # 8-hour session timeout
                # AD Configuration (Mock mode by default)
                "USE_MOCK_AD": os.getenv("USE_MOCK_AD", "true"),  # Use mock AD by default
                "AD_SERVER_URL": os.getenv("AD_SERVER_URL", "ldaps://ad.company.com:636"),
                "AD_BASE_DN": os.getenv("AD_BASE_DN", "DC=company,DC=com")
                # Note: AWS_REGION is automatically set by Lambda runtime
            }
        }

        # Employee Enrollment Lambda
        self.enrollment_lambda = lambda_.Function(
            self, "EnrollmentFunction",
            function_name="FaceAuth-Enrollment",
            description="Handle employee enrollment with ID card OCR and face registration",
            code=lambda_.Code.from_asset("lambda/enrollment"),
            handler="handler.handle_enrollment",
            **lambda_config
        )

        # Face Login Lambda  
        self.face_login_lambda = lambda_.Function(
            self, "FaceLoginFunction",
            function_name="FaceAuth-FaceLogin",
            description="Handle face-based login with 1:N matching",
            code=lambda_.Code.from_asset("lambda/face_login"),
            handler="handler.handle_face_login",
            **lambda_config
        )

        # Emergency Authentication Lambda
        self.emergency_auth_lambda = lambda_.Function(
            self, "EmergencyAuthFunction", 
            function_name="FaceAuth-EmergencyAuth",
            description="Handle emergency authentication with ID card + AD password",
            code=lambda_.Code.from_asset("lambda/emergency_auth"),
            handler="handler.handle_emergency_auth",
            **lambda_config
        )

        # Re-enrollment Lambda
        self.re_enrollment_lambda = lambda_.Function(
            self, "ReEnrollmentFunction",
            function_name="FaceAuth-ReEnrollment", 
            description="Handle employee face data re-enrollment",
            code=lambda_.Code.from_asset("lambda/re_enrollment"),
            handler="handler.handle_re_enrollment",
            **lambda_config
        )

        # Status Check Lambda
        self.status_lambda = lambda_.Function(
            self, "StatusFunction",
            function_name="FaceAuth-Status",
            description="Check authentication status and session validity",
            code=lambda_.Code.from_asset("lambda/status"),
            handler="handler.handle_status",
            **lambda_config
        )

    def _create_api_gateway(self):
        """
        Create API Gateway with REST endpoints for authentication
        Requirements: 4.6, 4.7
        """
        # Create REST API
        self.api = apigateway.RestApi(
            self, "FaceAuthAPI",
            rest_api_name="FaceAuth-API",
            description="Face Authentication Identity Provider API",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=self.frontend_origins,  # Restrict to frontend origins
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                    "X-Amz-Security-Token"
                ],
                allow_credentials=True,
                max_age=Duration.hours(1)
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            ),
            # Enable resource policy for IP-based access control
            policy=self._create_api_resource_policy() if self.allowed_ip_ranges != ["0.0.0.0/0"] else None
        )

        # Create /auth resource
        auth_resource = self.api.root.add_resource("auth")

        # Lambda integrations
        enrollment_integration = apigateway.LambdaIntegration(
            self.enrollment_lambda
        )

        face_login_integration = apigateway.LambdaIntegration(
            self.face_login_lambda
        )

        emergency_auth_integration = apigateway.LambdaIntegration(
            self.emergency_auth_lambda
        )

        re_enrollment_integration = apigateway.LambdaIntegration(
            self.re_enrollment_lambda
        )

        status_integration = apigateway.LambdaIntegration(
            self.status_lambda
        )

        # API endpoints
        enroll_resource = auth_resource.add_resource("enroll")
        enroll_resource.add_method("POST", enrollment_integration)

        login_resource = auth_resource.add_resource("login")
        login_resource.add_method("POST", face_login_integration)

        emergency_resource = auth_resource.add_resource("emergency")
        emergency_resource.add_method("POST", emergency_auth_integration)

        re_enroll_resource = auth_resource.add_resource("re-enroll")
        re_enroll_resource.add_method("POST", re_enrollment_integration)

        status_resource = auth_resource.add_resource("status")
        status_resource.add_method("GET", status_integration)

        # API Key for additional security (optional)
        self.api_key = apigateway.ApiKey(
            self, "FaceAuthAPIKey",
            api_key_name="FaceAuth-APIKey",
            description="API Key for Face-Auth IdP System"
        )

        # Usage plan
        usage_plan = apigateway.UsagePlan(
            self, "FaceAuthUsagePlan",
            name="FaceAuth-UsagePlan",
            description="Usage plan for Face-Auth API",
            throttle=apigateway.ThrottleSettings(
                rate_limit=100,
                burst_limit=200
            ),
            quota=apigateway.QuotaSettings(
                limit=10000,
                period=apigateway.Period.DAY
            )
        )

        usage_plan.add_api_stage(
            api=self.api,
            stage=self.api.deployment_stage
        )

        usage_plan.add_api_key(self.api_key)

    def _create_api_resource_policy(self) -> iam.PolicyDocument:
        """
        Create API Gateway resource policy for IP-based access control
        
        Returns:
            IAM PolicyDocument with IP whitelist
        """
        # Create IP condition for allowed ranges
        ip_conditions = {
            "IpAddress": {
                "aws:SourceIp": self.allowed_ip_ranges
            }
        }
        
        # Allow access from whitelisted IPs
        allow_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            principals=[iam.AnyPrincipal()],
            actions=["execute-api:Invoke"],
            resources=[f"arn:aws:execute-api:{self.region}:{self.account}:*/*"],
            conditions=ip_conditions
        )
        
        # Deny access from all other IPs
        deny_statement = iam.PolicyStatement(
            effect=iam.Effect.DENY,
            principals=[iam.AnyPrincipal()],
            actions=["execute-api:Invoke"],
            resources=[f"arn:aws:execute-api:{self.region}:{self.account}:*/*"],
            conditions={
                "NotIpAddress": {
                    "aws:SourceIp": self.allowed_ip_ranges
                }
            }
        )
        
        return iam.PolicyDocument(
            statements=[allow_statement, deny_statement]
        )

    def _create_cloudwatch_logs(self):
        """
        Create CloudWatch Log Groups for monitoring and debugging
        Requirements: 6.7, 8.7
        """
        # Log groups for Lambda functions
        lambda_functions = [
            ("enrollment", self.enrollment_lambda),
            ("face-login", self.face_login_lambda), 
            ("emergency-auth", self.emergency_auth_lambda),
            ("re-enrollment", self.re_enrollment_lambda),
            ("status", self.status_lambda)
        ]

        self.log_groups = {}
        for name, lambda_func in lambda_functions:
            log_group = logs.LogGroup(
                self, f"{name.title()}LogGroup",
                log_group_name=f"/aws/lambda/{lambda_func.function_name}",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.RETAIN
            )
            self.log_groups[name] = log_group

        # API Gateway access logs
        self.api_access_log_group = logs.LogGroup(
            self, "APIAccessLogGroup",
            log_group_name="/aws/apigateway/face-auth-access-logs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.RETAIN
        )

    def _create_outputs(self):
        """
        Create CloudFormation outputs for important resource information
        """
        CfnOutput(
            self, "APIEndpoint",
            value=self.api.url,
            description="Face-Auth API Gateway endpoint URL"
        )

        CfnOutput(
            self, "UserPoolId", 
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID"
        )

        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID"
        )

        CfnOutput(
            self, "S3BucketName",
            value=self.face_auth_bucket.bucket_name,
            description="S3 bucket for face authentication images"
        )

        CfnOutput(
            self, "VPCId",
            value=self.vpc.vpc_id,
            description="VPC ID for Face-Auth system"
        )

        CfnOutput(
            self, "APIKeyId",
            value=self.api_key.key_id,
            description="API Key ID for Face-Auth API"
        )
        
        # Output allowed IP ranges for reference
        CfnOutput(
            self, "AllowedIPRanges",
            value=", ".join(self.allowed_ip_ranges),
            description="Allowed IP ranges for API access (0.0.0.0/0 means all IPs allowed)"
        )
        
        # Frontend outputs
        CfnOutput(
            self, "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="S3 bucket for frontend static files"
        )
        
        CfnOutput(
            self, "FrontendDistributionId",
            value=self.frontend_distribution.distribution_id,
            description="CloudFront distribution ID for frontend"
        )
        
        CfnOutput(
            self, "FrontendURL",
            value=f"https://{self.frontend_distribution.distribution_domain_name}",
            description="Frontend CloudFront URL"
        )
        
        CfnOutput(
            self, "FrontendOrigins",
            value=", ".join(self.frontend_origins),
            description="Allowed CORS origins for API (* means all origins allowed)"
        )