<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Auto-generated Migration: Please modify to your needs!
 */
final class Version20221220222609 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Add price in member_subscription';
    }

    public function up(Schema $schema): void
    {
        // this up() migration is auto-generated, please modify it to your needs
        $this->addSql('ALTER TABLE member_subscription ADD COLUMN price INTEGER DEFAULT NULL');
    }

    public function down(Schema $schema): void
    {
        // this down() migration is auto-generated, please modify it to your needs
        $this->addSql('CREATE TEMPORARY TABLE __temp__member_subscription AS SELECT id, subscription_id, member_id, type, created_at, updated_at FROM member_subscription');
        $this->addSql('DROP TABLE member_subscription');
        $this->addSql('CREATE TABLE member_subscription (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, subscription_id INTEGER NOT NULL, member_id INTEGER NOT NULL, type VARCHAR(255) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, CONSTRAINT FK_D675FA5B9A1887DC FOREIGN KEY (subscription_id) REFERENCES subscription (id) NOT DEFERRABLE INITIALLY IMMEDIATE, CONSTRAINT FK_D675FA5B7597D3FE FOREIGN KEY (member_id) REFERENCES member (id) NOT DEFERRABLE INITIALLY IMMEDIATE)');
        $this->addSql('INSERT INTO member_subscription (id, subscription_id, member_id, type, created_at, updated_at) SELECT id, subscription_id, member_id, type, created_at, updated_at FROM __temp__member_subscription');
        $this->addSql('DROP TABLE __temp__member_subscription');
        $this->addSql('CREATE INDEX IDX_D675FA5B9A1887DC ON member_subscription (subscription_id)');
        $this->addSql('CREATE INDEX IDX_D675FA5B7597D3FE ON member_subscription (member_id)');
    }
}
