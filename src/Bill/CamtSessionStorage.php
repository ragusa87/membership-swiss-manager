<?php

namespace App\Bill;

use Genkgo\Camt\DTO\Message;
use Symfony\Component\HttpFoundation\Exception\SessionNotFoundException;
use Symfony\Component\HttpFoundation\RequestStack;
use Symfony\Component\HttpFoundation\Session\Session;
use Symfony\Component\HttpFoundation\Session\SessionInterface;
use Symfony\Component\HttpFoundation\Session\Storage\MockArraySessionStorage;

class CamtSessionStorage
{
    private RequestStack $requestStack;

    public function __construct(RequestStack $requestStack)
    {
        $this->requestStack = $requestStack;
    }

    public function set(string $id, Message $message): void
    {
        $this->getSession()->set($id, $message);
        $this->addId($id);
    }

    public function get(string $id): ?Message
    {
        return $this->getSession()->get($id);
    }

    public function remove(string $id): void
    {
        $this->getSession()->remove($id);
        $this->removeId($id);
    }

    protected function getSession(): SessionInterface
    {
        try {
            return $this->requestStack->getSession();
        } catch (SessionNotFoundException) {
            return new Session(new MockArraySessionStorage());
        }
    }

    /**
     * @return array<string>
     */
    public function getIds(): array
    {
        return $this->getSession()->get('camt_ids', []);
    }

    private function addId(string $id): void
    {
        $ids = $this->getSession()->get('camt_ids', []);
        $ids[] = $id;
        $this->getSession()->set('camt_ids', $ids);
    }

    private function removeId(string $id): void
    {
        $ids = $this->getSession()->get('camt_ids', []);
        $key = array_search($id, $ids, true);
        if (false !== $key) {
            unset($ids[$key]);
        }
        $this->getSession()->set('camt_ids', $ids);
    }
}
