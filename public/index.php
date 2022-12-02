<?php
$_SERVER['HTTP_X_FORWARDED_PROTO'] = $_SERVER['HTTP_CUSTOM_FORWARDED_PROTO'] ?? $_SERVER['HTTP_X_FORWARDED_PROTO'] ?? 'http';

use App\Kernel;

require_once dirname(__DIR__).'/vendor/autoload_runtime.php';

return function (array $context) {
    return new Kernel($context['APP_ENV'], (bool) $context['APP_DEBUG']);
};
