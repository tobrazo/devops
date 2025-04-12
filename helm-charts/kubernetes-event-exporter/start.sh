#!/bin/bash -x

nameSpace="kube-system"
repoChart="https://charts.bitnami.com/bitnami"
repoProject="kubernetes-event-exporter"
chartName="kubernetes-event-exporter"
chartVersion="2.7.6"
historySize="10"
appOps="$1"

verifying_templates () {
  helm repo add ${repoProject} ${repoChart}
  helm repo update
  helm fetch ${repoProject}/${chartName} --untar
  mkdir ${repoProject}/package
  helm template ${repoProject} ${repoProject}/ --values ./test-env/replace.yaml --dry-run
  helm package --debug ${repoProject}/ -d ${repoProject}/package
  rm -rf ${repoProject}/
}

case ${appOps} in
  install)
    verifying_templates
    kubectl --namespace=${nameSpace} apply -f ./additional-configmap.yaml
    helm install ${chartName} ${repoProject}/${chartName} -f ./test-env/replace.yaml --namespace=${nameSpace}
  ;;
  upgrade)
    verifying_templates
    helm upgrade --atomic --history-max ${historySize} ${chartName} ${repoProject}/${chartName} -f ./test-env/replace.yaml --namespace=${nameSpace}
  ;;
  delete)
    echo "Deleting Helm Chart ${chartName}"
    helm uninstall ${chartName} --namespace=${nameSpace}
    echo "Deleting configMap http_ca"
    kubectl delete --namespace=${nameSpace} -f ./additional-configmap.yaml
  ;;
  debug)
    echo "Debug mode !"
    verifying_templates
    helm install --dry-run --debug ${chartName} --namespace ${nameSpace} -f ./test-env/replace.yaml ${repoProject}/${chartName}
  ;;
  *)
    echo "Set requirements !"
  ;;
esac
