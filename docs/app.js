var app = angular.module('delegateApp', []);

app.controller('indexCtrl', function($scope, $http) {
    $scope.accounts = [];
    $scope.accounts = [];
    $scope.lastpayout = 0;
    $scope.nextpayout = 0;

    $http.get ('poollogs.json').then (function (res) {
        $scope.lastpayout = res.data.lastpayout * 1000;
        $scope.nextpayout = moment ($scope.lastpayout).add (1, 'day').valueOf();
        $scope.accounts = [];
	$scope.standby = [];
	$scope.weight = res.data.weight;
	$scope.kapuperday = res.data.kapuperday;

        for (addr in res.data.accounts) {
            var it = res.data.accounts[addr];
            it['address'] = addr;
            $scope.accounts.push (it);
        }

        for (addr in res.data.standby) {
            var it = res.data.standby[addr];
            it['address'] = addr;
            $scope.standby.push (it);
        }
    });

    $http.get ('http://212.237.60.84:9700/api/delegates/get?username=maxwell.pool').then (function (res) {
        $scope.delegate = res.data.delegate;
    });
});
