<?php

namespace App\Helper;

use App\Entity\Member;
use Doctrine\Persistence\ManagerRegistry;
use Psr\Log\LoggerInterface;

class MemberMatcher
{
    public function __construct(protected ManagerRegistry $managerRegistry, protected ?LoggerInterface $logger)
    {
    }

    protected function getRepo(): \Doctrine\Persistence\ObjectRepository
    {
        return $this->managerRegistry->getManager()->getRepository(Member::class);
    }

    protected function matches(Member $source, array $criteria, int $score, ?string $hint): ?MemberMatch
    {
        $match = $this->getRepo()->findOneBy(
            $criteria
        );

        return $match ? (new MemberMatch($source, $match, $score))->setHint($hint) : null;
    }

    protected function findByFullName(Member $user, array $criteria = []): ?MemberMatch
    {
        if (empty($user->getFirstname()) || empty($user->getLastname())) {
            return null;
        }

        return $this->matches($user, [
                'firstname' => $user->getFirstname(),
                'lastname' => $user->getLastname(),
            ] + $criteria, MemberMatch::SCORE_MEDIUM, 'fullname');
    }

    protected function findByPhoneAndFirstName(Member $user, array $criteria = []): ?MemberMatch
    {
        if (empty($user->getPhone()) || empty($user->getFirstname())) {
            return null;
        }

        return $this->matches($user, [
                'phone' => $user->getPhone(),
                'firstname' => $user->getFirstname(),
            ] + $criteria, MemberMatch::SCORE_HIGH, 'phone+firstname');
    }

    protected function findByEmailAndFirstName(Member $user, array $criteria = []): ?MemberMatch
    {
        if (empty($user->getEmail())) {
            return null;
        }

        return $this->matches($user, [
                'email' => $user->getEmail(),
                'firstname' => $user->getFirstname(),
            ] + $criteria, MemberMatch::SCORE_HIGH, 'email+firstname');
    }

    protected function findByEmail(Member $user, array $criteria = []): ?MemberMatch
    {
        if (empty($user->getEmail())) {
            return null;
        }

        return $this->matches($user, [
                'email' => $user->getEmail(),
            ] + $criteria, MemberMatch::SCORE_LOW, 'email');
    }

    public function find(Member $user): MemberMatch
    {
        $parent = $user->getParent();
        // For children, we try to find one with the same parents
        if (null !== $parent) {
            if (null !== $parent->getParent()) {
                $this->logger?->warning('User with a 2 level parent hierarchy is not supported');
                $this->logger?->debug('Remove parent of '.(string) $parent);
                $parent = clone $parent;
                $parent->getParent()->setParent(null);
            }
            $parentMatch = $this->find($parent);
            $parent = $parentMatch->getResult();
            // If we are not sure that we found the same parent, force a mismatch.
            if (null !== $parent && $parentMatch->getScore() < MemberMatch::SCORE_MEDIUM) {
                $this->logger?->debug('Skip parent match as too weak: '.(string) $parent);

                return MemberMatch::zero($user);
            }
        }

        // Search a similar user, we try to map ~2 fields when possible, then 1
        return $this->findByEmailAndFirstName($user) ??
            $this->findByPhoneAndFirstName($user) ??
            $this->findByFullNameAndAddress($user, ['parent' => $parent]) ??
            $this->findByFullName($user, ['parent' => $parent]) ??
            $this->findByEmail($user, ['parent' => $parent]) ??
            MemberMatch::zero($user);
    }

    private function findByFullNameAndAddress(Member $user, array $criteria = [])
    {
        if (
            empty($user->getFirstname()) ||
            empty($user->getLastname()) ||
            empty($user->getAddress() ||
                empty($user->getCity()) ||
                empty($user->getZip())
            )) {
            return null;
        }

        return $this->matches($user, [
                'firstname' => $user->getFirstname(),
                'lastname' => $user->getLastname(),
                'address' => $user->getAddress(),
                'city' => $user->getCity(),
                'zip' => $user->getZip(),
            ] + $criteria, MemberMatch::SCORE_HIGH, 'fullname+address');
    }
}
