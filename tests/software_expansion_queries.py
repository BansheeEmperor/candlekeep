"""Multi-hop expansion queries for Track 2 benchmark on software corpus.

Each query mentions entity_a only. Ground truth = docs containing entity_b
but not entity_a — tests whether the system surfaces related-concept documents
not directly mentioned in the query.

Entity pairs derived from co-occurrence analysis of scale_docs + sample_docs
using the default tech token extractor (CamelCase, SCREAMING_SNAKE, dotted IDs).
"""

SOFTWARE_EXPANSION_QUERIES = [
    {
        "query": "How do I implement OAuth 2.0 authorization in a web application?",
        "entity_a": "OAuth",
        "entity_b": "HttpOnly",
        "rationale": "OAuth docs co-occur with cookie security (HttpOnly flag); "
                     "HttpOnly-only docs cover XSS/cookie hardening not mentioned in OAuth context",
    },
    {
        "query": "How does CloudWatch help with monitoring distributed systems?",
        "entity_a": "CloudWatch",
        "entity_b": "CloudFormation",
        "rationale": "CloudWatch monitoring docs co-occur with CloudFormation; "
                     "CloudFormation-only docs cover IaC deployment not in monitoring context",
    },
    {
        "query": "How do I use SparkSession to process large datasets?",
        "entity_a": "SparkSession",
        "entity_b": "pyspark.sql.functions",
        "rationale": "SparkSession docs co-occur with pyspark functions; "
                     "data lake architecture docs use pyspark functions without SparkSession context",
    },
    {
        "query": "What are RESTful API design best practices?",
        "entity_a": "RESTful",
        "entity_b": "CloudFormation",
        "rationale": "REST API docs co-occur with CloudFormation in serverless/well-architected contexts",
    },
    {
        "query": "How does auto-scaling work with ScalingAdjustment policies?",
        "entity_a": "ScalingAdjustment",
        "entity_b": "DevOps",
        "rationale": "Auto-scaling docs co-occur with DevOps; CI/CD and config management docs "
                     "cover DevOps practices without auto-scaling specifics",
    },
    {
        "query": "What security considerations apply when using AppArmor for container isolation?",
        "entity_a": "AppArmor",
        "entity_b": "JavaScript",
        "rationale": "AppArmor security docs co-occur with JavaScript in API security context; "
                     "JS-only docs cover client-side security not in AppArmor context",
    },
    {
        "query": "How do I configure WatermarkStrategy for event-time processing in streaming?",
        "entity_a": "WatermarkStrategy",
        "entity_b": "pyspark.sql.functions",
        "rationale": "Watermark/streaming docs co-occur with pyspark; "
                     "data lake docs use pyspark without watermark context",
    },
    {
        "query": "What are best practices for using KafkaSink in stream processing pipelines?",
        "entity_a": "KafkaSink",
        "entity_b": "pyspark.sql.functions",
        "rationale": "Kafka sink docs co-occur with pyspark in streaming context",
    },
    {
        "query": "How does CloudFormation handle infrastructure deployment and rollback?",
        "entity_a": "CloudFormation",
        "entity_b": "PowerShell",
        "rationale": "CloudFormation docs co-occur with PowerShell in disaster recovery / "
                     "penetration testing contexts",
    },
    {
        "query": "What are the security implications of HttpOnly cookies in web applications?",
        "entity_a": "HttpOnly",
        "entity_b": "AppArmor",
        "rationale": "HttpOnly cookie docs co-occur with AppArmor in container security context",
    },
]
