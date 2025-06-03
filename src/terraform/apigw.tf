resource oci_apigateway_gateway starter_apigw {
  compartment_id = local.lz_web_cmp_ocid
  display_name  = "${var.prefix}-apigw"
  endpoint_type = "PUBLIC"
  subnet_id = data.oci_core_subnet.starter_web_subnet.id
  freeform_tags = local.freeform_tags       
}

locals {  
  db_root_url = replace(data.oci_database_autonomous_database.starter_atp.connection_urls[0].apex_url, "/ords/apex", "" )
}   

# One single entry "/" would work too. 
# The reason of the 3 entries is to allow to make it work when the APIGW is shared with other URLs (ex: testsuite)
resource "oci_apigateway_deployment" "starter_apigw_deployment_ords" {
  compartment_id = local.lz_app_cmp_ocid
  display_name   = "${var.prefix}-apigw-deployment"
  gateway_id     = oci_apigateway_gateway.starter_apigw.id
  path_prefix    = "/ords"
  specification {
    # Go directly from APIGW to APEX in the DB    
    routes {
      path    = "/{pathname*}"
      methods = [ "ANY" ]
      backend {
        type = "HTTP_BACKEND"
        url    = "${local.db_root_url}/ords/$${request.path[pathname]}"
        connect_timeout_in_seconds = 60
        read_timeout_in_seconds = 120
        send_timeout_in_seconds = 120            
      }
      request_policies {
        header_transformations {
          set_headers {
            items {
              name = "Host"
              values = ["$${request.headers[Host]}"]
            }
          }
        }
      }
    }
  }
  freeform_tags = local.freeform_tags
}

resource "oci_apigateway_deployment" "starter_apigw_deployment_i" {
  compartment_id = local.lz_app_cmp_ocid
  display_name   = "${var.prefix}-apigw-deployment"
  gateway_id     = oci_apigateway_gateway.starter_apigw.id
  path_prefix    = "/i"
  specification {
    # Go directly from APIGW to APEX in the DB    
    routes {
      path    = "/{pathname*}"
      methods = [ "ANY" ]
      backend {
        type = "HTTP_BACKEND"
        url    = "${local.db_root_url}/i/$${request.path[pathname]}"
        connect_timeout_in_seconds = 60
        read_timeout_in_seconds = 120
        send_timeout_in_seconds = 120            
      }
      request_policies {
        header_transformations {
          set_headers {
            items {
              name = "Host"
              values = ["$${request.headers[Host]}"]
            }
          }
        }
      }
    }
  }
  freeform_tags = local.freeform_tags
}