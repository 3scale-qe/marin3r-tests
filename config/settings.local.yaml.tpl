#default:
#  openshift:
#    project: "kuadrant"                       # Optional: namespace for tests to run, if None uses current project
#    api_url: "https://api.openshift.com"      # Optional: OpenShift API URL, if None it will OpenShift that you are logged in
#    token: "KUADRANT_RULEZ"                   # Optional: OpenShift Token, if None it will OpenShift that you are logged in
#    kubeconfig_path: "~/.kube/config"         # Optional: Kubeconfig to use, if None the default one is used
#  cfssl: "cfssl"  # Path to the CFSSL library for TLS tests
#  envoy:
#    image: "docker.io/envoyproxy/envoy:v1.23-latest"  # Envoy image that should be deployed