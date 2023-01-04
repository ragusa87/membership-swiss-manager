<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Auto-generated Migration: Please modify to your needs!
 */
final class Version20230104230339 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Add address number to members';
    }

    public function up(Schema $schema): void
    {
        // this up() migration is auto-generated, please modify it to your needs
        $this->addSql('CREATE TEMPORARY TABLE __temp__member AS SELECT id, parent_id, firstname, lastname, email, comment, address, city, phone, zip, created_at, updated_at FROM member');
        $this->addSql('DROP TABLE member');
        $this->addSql('CREATE TABLE member (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, parent_id INTEGER DEFAULT NULL, firstname VARCHAR(255) NOT NULL, lastname VARCHAR(255) DEFAULT NULL, email VARCHAR(255) DEFAULT NULL, comment CLOB DEFAULT NULL, address VARCHAR(255) DEFAULT NULL, city VARCHAR(255) DEFAULT NULL, phone VARCHAR(255) DEFAULT NULL, zip INTEGER DEFAULT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, address_number VARCHAR(20) DEFAULT NULL, CONSTRAINT FK_70E4FA78727ACA70 FOREIGN KEY (parent_id) REFERENCES member (id) ON UPDATE NO ACTION ON DELETE NO ACTION NOT DEFERRABLE INITIALLY IMMEDIATE)');
        $this->addSql('INSERT INTO member (id, parent_id, firstname, lastname, email, comment, address, city, phone, zip, created_at, updated_at) SELECT id, parent_id, firstname, lastname, email, comment, address, city, phone, zip, created_at, updated_at FROM __temp__member');
        $this->addSql('DROP TABLE __temp__member');
        $this->addSql('CREATE INDEX IDX_70E4FA78727ACA70 ON member (parent_id)');
    }

    public function down(Schema $schema): void
    {
        // this down() migration is auto-generated, please modify it to your needs
        $this->addSql('CREATE TEMPORARY TABLE __temp__member AS SELECT id, parent_id, firstname, lastname, email, comment, address, city, phone, zip, created_at, updated_at FROM member');
        $this->addSql('DROP TABLE member');
        $this->addSql('CREATE TABLE member (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, parent_id INTEGER DEFAULT NULL, firstname VARCHAR(255) NOT NULL, lastname VARCHAR(255) DEFAULT NULL, email VARCHAR(255) DEFAULT NULL, comment CLOB DEFAULT NULL, address VARCHAR(255) DEFAULT NULL, city VARCHAR(255) DEFAULT NULL, phone VARCHAR(255) DEFAULT NULL, zip INTEGER DEFAULT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, CONSTRAINT FK_70E4FA78727ACA70 FOREIGN KEY (parent_id) REFERENCES member (id) NOT DEFERRABLE INITIALLY IMMEDIATE)');
        $this->addSql('INSERT INTO member (id, parent_id, firstname, lastname, email, comment, address, city, phone, zip, created_at, updated_at) SELECT id, parent_id, firstname, lastname, email, comment, address, city, phone, zip, created_at, updated_at FROM __temp__member');
        $this->addSql('DROP TABLE __temp__member');
        $this->addSql('CREATE UNIQUE INDEX UNIQ_70E4FA78727ACA70 ON member (parent_id)');
    }
}
