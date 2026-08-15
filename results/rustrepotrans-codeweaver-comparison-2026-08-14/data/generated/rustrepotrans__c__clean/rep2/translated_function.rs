pub fn clean(&mut self) {
        self.pool_ptr = 0;
        self.rndptr = 0;
        self.pool.fill(0);
        self.ira.fill(0);
        self.borrow = 0;
    }
